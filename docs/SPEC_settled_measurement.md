# SPEC — ONE FILL, ONE WAIT, ONE BEST MEASUREMENT

> **Status: ⭐ LARGELY BUILT.** §27 (2026-08-17) · §30.16 · §31.11a · and ⭐⭐ **§51 — phases 0·A·B·E·C·D of
> §46/§50, built 2026-08-20, 511 tests green.** ⏸ **The rig click-through of §51 is owed**, and the
> constants still rest on four clean fills of one oil on one evening (§35's T1).
>
> ⚠ Sections are kept in the order they were written, not in the order they are true: **later sections
> correct earlier ones and say so.** The fastest honest entry points are **§50** (what to build), **§51**
> (what was built), and **§47** (what is still open).
>
> *Originally: DESIGN, 2026-08-15, no code written — the highest priority, preceding the σ_fill run, the
> refill test and the lamp rebuild, because every one of those is an attempt to measure something stable
> and until this lands the instrument does not produce one.*
>
> Evidence base: `SPEC_capture_quality.md` §16.36 (the lamp changes the sample), §16.34.3d (the σ_fill
> design change), `SPEC_metric_research.md` §10. Prototype and every number below:
> `diagnostics/clearing_time_course.py`.
>
> ⭐ **2026-08-16 — three sections added, and they change the shape of §2.** §9 the **ring buffer**
> (per-frame evaluation of a rolling window, and why the water bath makes it necessary rather than
> merely nicer), §10 the **shared object** that keeps the diagnostic script and the plugin on one
> algorithm, §11 the pre-registered **heat-dose experiment** — which is the go/no-go gate on §7's heated
> holder. ⛔ §3's "never take more captures than needed" is corrected there.

---

## 1 · The problem, in one paragraph

A muddy fill entering the beam is doing **two things at once**: the lamp's heat **clears** it (turbidity
falls, `Q%` falls) and the lamp's light **browns** it (pigment is destroyed, `Q%` rises). The first
decays, the second grows, and they cross. ⇒ **there is exactly one moment when the sample is worth
measuring**, and the operator cannot see it — but the instrument can.

```
Q%  26.06 ┐ turbid: no verdict at all (§3.1a)
          │
    13.27 ┴── the minimum, t ≈ 17 min ── the ONLY honest reading
          │
    14.73 ┘ 72 min later: +1.46 units = 7 refill floors of photodamage
```

⛔ **This is not a refinement of the 15-minute rule; it is what the 15-minute rule was reaching for.**
Waiting a fixed time gets the moment right only by luck, because clearing time varies with the oil, the
dose, room temperature and the lamp's warm-up state.

---

## 2 · What the device must do

```
ACQUISITION
  1  capture reference (once)
  2  capture sample repeatedly, every N seconds
  3  after each capture:  A_Soret, A_valley, A_Q  ->  Q%
  4  GATE      has the clearing finished?     |ΔA_valley| < 0.005, twice running
  5  READ      the Q% minimum, as a parabola vertex through its three neighbours
  6  STOP      once the minimum is confirmed (a rise > 3σ after it, or a fixed ceiling)
  7  REPORT    the best value + the whole curve + the accumulated lamp-on time
```

### 2.1 ⭐ Gate on `A_valley`, not on `Q%`

The obvious rule — *"wait until `Q%` stops falling and rises three times"* — **works and costs ten
minutes of light** (measured: it fires at t = 26.5 against a true minimum at t = 16.7). It has to wait
because it is detecting a sign change on a quantity whose no-re-seat floor is sd 0.063.

⭐ `A_valley` is the **cause**, not the symptom: it falls **97 %** (0.9455 → 0.0257) and then flattens.
Gating on `|ΔA_valley| < 0.005` for two consecutive samples fires at **t = 16.7 — the same sample, with
no extra dose.**

### 2.2 ⭐ Read a vertex, not the minimum

The minimum of `n` noisy samples is biased low by ~0.9 sd (~0.06 here) because it selects the most
negative excursion. A parabola through the three samples around it averages instead of selecting.

### 2.3 ⚠ Report the zero-dose extrapolation SEPARATELY

Even the minimum is already damaged — on 2026-08-14, **0.36 units = 1.7 refill floors** had accumulated
before clearing finished. Fitting the post-clearing damage line back to insertion estimates it out.
⛔ **Never folded into the answer**: it assumes the damage rate during clearing matched the rate after,
while the sample was turbid and the light distribution inside it was quite different.

### ⭐ 2.4 LOG THE CLEARING TIME — it is a σ_fill component, not a diagnostic curiosity

Damage accumulates while the fill clears, and **clearing time varies between fills** (oil, dose, room
temperature, lamp warm-up state). At the measured +1.0 to +1.6 `Q%` per hour:

| clearing time varies by | the damage term varies by |
|---|---|
| ±3 min | 0.05-0.08 units |
| ±5 min | 0.08-0.13 units |
| ±10 min | 0.17-0.27 units |

Against the 0.21 refill floor that is **material but not dominant** — so it belongs INSIDE σ_fill's
budget rather than outside it. ⇒ **every measurement records its clearing time alongside its value**, so
the correlation between the two can be checked directly instead of assumed away, and §2.3's zero-dose
extrapolation becomes the correction for it rather than a footnote.
⭐ `SPEC_history_tracker.md` §9.0 carries the consequence for the alarm band.

### 2.5 The guards, all three already implemented in the plugin

| | |
|---|---|
| **§3.1** `A_Soret` < 0.15 | the MEASUREMENT is broken — nothing reported at all |
| **§3.1a** `Q%` outside 12–22 | the SAMPLE is out of domain — value reported, **verdict withheld** |
| ⭐ NEW | **`A_valley` never flattens** — the fill never cleared, so there is no best value. Say so; do not report the last sample as though it were one |

---

## 3 · What it must NOT do

⛔ **Never report a fixed-time reading.** The whole point is that the moment is discovered, not assumed.

⛔ **Never average across the curve.** The samples are not replicates of one quantity — they are a
trajectory through two changing states. Averaging them mixes turbidity into the answer.
⚠ **Refined by §9.3** (2026-08-16): a *rolling* window is not "averaging across the curve" provided the
window is short against the process it tracks. The prohibition is on collapsing the trajectory to one
number, not on smoothing it. §9.3 gives the arithmetic that says when a window is short enough.

⛔ **Never take more captures than needed.** Every capture is light, and light is damage. Stop when the
minimum is confirmed. ⚠ At production dose this is ~1–2 % of a diagnostic run, which is why
§16.36.4 concludes this is not a product problem — but only if the device stops.
⛔ **CORRECTION, 2026-08-16 — this sentence is wrong as written, and §9.4 replaces it.** A *capture* is
not a dose. **The lamp is on continuously**; the camera is a passive receiver, so reading 1 frame or
1000 while the jar sits in the beam costs exactly the same light. What costs dose is **lamp-on time with
the jar inserted**. ⇒ per-frame evaluation is FREE today, and the rule that survives is "**stop the
run** when the answer is in", not "take fewer frames". ⚠ It becomes true again the day a shutter exists
— see §9.4.

⚠ **Never use `DN` as the readiness signal.** §16.36.6: the guard's DN ran at **1.07–2.30 linear counts**
all evening and sat frozen at exactly 30.0 encoded for six readings while `A_Soret` fell 3.9 % and `Q%`
rose 0.56. **DN stops changing when it runs out of bits, not when the sample stops changing.**

---

## 4 · What the operator sees

A coach line, in the §-acquisition-guidance style already shipped:

```
   clearing …            4:32   turbidity still falling
   clearing …           12:10   nearly there
   ⭐ settled at 16:42 — measuring
   ✅ Q% 13.3   good — green        (17 min, 21 captures)
```

⚠ **The wait is accepted deliberately** (Edwin, 2026-08-15): equilibration time is ordinary analytical
practice, it is explainable to a miller, and it avoids the heated-holder complication. ⇒ the UI's job is
to make the wait legible, not to hide it.

---

## 5 · Why this precedes everything else

| queued work | why it must wait |
|---|---|
| **σ_fill / the refill test** | it measures the reproducibility OF A MEASUREMENT. Until the measurement is defined, it measures the protocol's own drift — §16.34.3d. ✅ **UNBLOCKED: series F (§28) is the first σ_fill taken under a defined measurement** |
| **the DIY lamp rebuild** | a new lamp changes the scale by 4.84 units (§10.4). Re-deriving thresholds on a drifting measurement bakes the drift into the new scale |
| **the internal PDFs** | they would document numbers the next protocol supersedes |
| **PRIO 3a ground truth** | labels compared against a measurement that moves are labels compared against nothing. ✅ **UNBLOCKED, and MEASURED: §28.9 — the instrument now costs 3 % of a correlation, where the old protocol cost 32 %** |

⇒ ⭐ **Everything downstream assumes a measurement that can be trusted. This is that measurement.**

---

## 6 · Phasing

| PH | deliverable | gate |
|---|---|---|
| **S1** | the maths, headless: gate, vertex, zero-dose, guards — already in `diagnostics/clearing_time_course.py` | reproduces the 2026-08-14 curve: settled at t ≈ 17, best `Q%` 13.27 |
| **S2** | lift them into the plugin/host as an ACQUISITION loop | unit tests on a synthetic clearing curve |
| **S3** | the operator coach line + the "never cleared" outcome | click-through |
| **S4** | persist the whole curve with the measurement | a saved run can be re-examined; the best-value choice is auditable, which matters because §16.34.3d makes it load-bearing |
| **S5** | rig verification on a muddy fill and a clean one | the clean fill must settle immediately and not wait 17 minutes for nothing |

⚠ **S5's second half is the one to watch.** A clean, already-dissolved oil has no clearing phase at all —
`A_valley` is flat from the first sample. The gate must fire immediately rather than demanding a decay
that never happens, or every good oil pays the muddy oils' 15-minute tax.

---

## ⭐ 7 · THE HEATED HOLDER — deferred, costed, and the shape it should take  *(Edwin's choice, 2026-08-15)*

> ⚠ **NOT ON THE CRITICAL PATH.** §1–§6 need **no hardware at all**: the lamp already clears the fill in
> ~17 min and that wait is accepted. This section exists so the option is specified when it is wanted,
> and so nothing is bought before the software that makes the buying decision possible.

### 7.1 What it would buy

| | |
|---|---|
| clearing time | ~17 min (lamp, ~40 °C) → **~2 min** (measured at 50 °C in a bath, §16.36.7) |
| pre-clearing damage | **0.36 units = 1.7 refill floors** (§2.3) → ~0 |
| the σ_fill clearing-time term | ±0.05–0.27 units (§2.4) → collapses with the clearing time |

⭐⭐ **And it is what would make a SHUTTER possible at all.** §16.36.7 found the conflict: the lamp's heat
is what holds the sample above its cloud point (35–40 °C), so shuttering the lamp re-clouds the sample.
⇒ **a shutter REQUIRES a heated holder**; the two are one decision, not two.

### 7.2 The build — Edwin's choice: silicone mat + a bought thermostat

```
    230 V ──▶ [12 V adapter]  ──▶ [thermostat module] ──▶ [silicone heating mat]
              isolated, ~€6         NTC probe ON THE RING     adhesive, 12 V, ~€10
                                                              ⇓ conducts into
    ⭐ everything past the adapter is SELV — touchable        [ALUMINIUM jar ring]
```

⭐ **The aluminium ring is required anyway**, independently of heating: PLA is already in its creep
regime at 40 °C (§16.36 cautions), and the ring doubles as the heat spreader.

⚠ **A self-regulating PTC element is the simpler alternative** — regulation is intrinsic to the part, so
there is no controller, no probe and no relay. It is fixed-temperature; the mat + thermostat is chosen
here because the set-point is still unknown and wants to be adjustable while the cloud point is being
characterised.

### ⛔ 7.3 PLACEMENT — conduct into the ring, never heat the air column

```
        │             │
        │  ███████    │  ← jar        ⭐ HEAT THE RING: conduction into the
      ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄   ← mat here      jar, almost no air warmed
        │             │
     ▄▄▄│             │▄▄▄  ⛔ NOT the cone wall: warm air rises THROUGH THE
        │             │        BEAM -> refractive streaming the camera sees
        ├═════════════┤
        │  ● ● ● ● ●  │     ⛔ NOT the lamp base: 11 cm away, and the same
        └─────────────┘        convection problem
```

⛔ §12.5 of `SPEC_lamp_rebuild.md` is explicit that what happens inside those tubes is either signal or
stray light. A thermal gradient in the optical path is neither, and the camera sees it directly.
⚠ The cone joint is also the *most* repeatable interface in the stack (0.39 % against the jar's 2.81 %,
§16.9.3h) — heating it puts thermal expansion into the one part that already behaves.

### ⚠ 7.4 SAFETY — SELV only, and no contacts near the solvent

⛔ **Never mains at the holder.** The jar is handled on every measurement, and **IPA's flash point is
12 °C** — its vapour sits exactly where a heater would go. Everything past the adapter must be 12 V.
⚠ **Prefer a solid-state (MOSFET/PWM) thermostat over a relay** for the same reason: a relay arcs, and
an arc next to solvent vapour is an ignition source.

### ⭐ 7.5 THE ACCEPTANCE TEST — it is free, and it is the noise floor

Run the null series (§16.26) with the heater ON and OFF.

```
   Q% no-re-seat sd stays near 0.063   ->  the heater does not disturb the beam  ⭐ accept
   it rises                            ->  convection in the optical path; move the heat
                                           further from the beam or reduce the power
```

⇒ ⭐ **The instrument's own floor is the acceptance criterion**, which is the cheapest possible test and
needs no new apparatus.

---

## ⭐⭐ 9 · THE RING BUFFER — continuous acquisition and per-frame evaluation  *(Edwin, 2026-08-16)*

> **Status: DESIGN.** The mechanism §2's loop needs. Today a "sample" is a **block**: grab 50–60 frames,
> mean them, get one number, sleep, repeat. Edwin's proposal: **hold the last N frames in a ring and
> re-evaluate after every frame**, so the curve is sampled ~50× more finely at no extra cost.
> ⭐ It is the right change, and §9.6 is the reason it is not merely a nicer chart.

### 9.1 What it is, precisely

```
  TODAY     [ 50 frames ]------------- 3 min -------------[ 50 frames ]---...
            └─ one row, t stamped at the block                 └─ one row

  RING      f f f f f f f f f f f f f f f f f f f f f f f f f f f f f f ...
            └────── window of 50 ──────┘ -> row
              └────── window of 50 ──────┘ -> row      one row PER FRAME,
                └────── window of 50 ──────┘ -> row    each a 50-frame mean
```

The ring holds **raw per-frame spectra**, not a running sum. At ~2600 ROI columns × 50 frames × 8 bytes
that is **≈ 1 MB** — so there is no reason to be clever: keep the frames, reduce the window on demand,
and the window length stays a parameter instead of a commitment (§9.3).

### ⭐⭐ 9.1a THREE DIFFERENT SIZES, AND CONFLATING THEM IS THE BUG  *(Edwin, 2026-08-16: "there must be some mechanism such that the snapshot that gave the best result can be retrieved — which would not be the case if it were already deleted in the ring buffer")*

⭐ **Edwin is right, and the fix is not a bigger ring.** "50" was doing three jobs at once. Separate them
and the retrieval problem disappears:

| | symbol | what it is | size |
|---|---|---|---|
| **evaluation window** | `W` | how many frames one row averages — the **statistical aperture** (§9.2/§9.3) | 50 |
| **retention** | `R` | how many raw frames stay in RAM. ⭐ **Only ever `W + margin`** | ~60 |
| ⭐ **the winner** | — | the **reduced mean spectrum of the best row so far**, *promoted OUT of the ring* the moment it is computed | 1 spectrum, ~20 KB |

⛔ **The best window is never "fished back out" of the ring** — by then its frames are gone, and any ring
big enough to prevent that is a ring sized by the run length instead of by the statistics. ⭐ Instead the
state machine **promotes**: when a row becomes the best-so-far it hands its already-computed mean
spectrum to a `best` slot, replacing the previous one. `R` stays bounded, retrieval is O(1), and the
answer's spectrum is a real capture, not a reconstruction.

```
   frames ──▶ [ ring R=60 ]──window W=50──▶ reduce ──▶ Row (scalars)
                    │                          │
                    │                          └──▶ if best-so-far: ⭐ PROMOTE the mean spectrum
                    │                                   ┌──────────────┐
                    └──▶ (diagnostics only)              │ best  ← 1   │  ⭐ survives the ring
                         append raw frame to .npz        │ nbrs  ← ±1  │  (±1 = the vertex's neighbours)
                         ⇒ RAM stays bounded             └──────────────┘
```

⚠ **The vertex read has no spectrum of its own.** §2.2 puts the *value* between two rows, where nothing
was captured. ⇒ report **two things, never one**: `bestRow` — a real, retrievable capture with its own
spectrum — and `vertexValue`, the refined scalar. They differ by well under the 0.063 floor; the report
and the PDF show `bestRow`'s spectrum, and the archive records both.

⭐ **The whole-run raw stream is a DIAGNOSTIC concern.** 20 minutes at ~1.4 fps is ~1700 frames ≈ 34 MB
— fine on the desktop bench, ⛔ not on Android.
⛔⛔ **CORRECTED by §25/X1:** this paragraph first said "append-as-you-go, so RAM stays bounded". ⛔ There
is **no append mode for `.npz`** — the archive is written once. ⇒ the script **holds the run in RAM and
writes in `finally:`** (34 MB, and it is the same flush the Ctrl-C case needs). ⭐ `R` stays bounded for
the **engine**; the **script** separately holds everything — two buffers, two lifetimes.

### ⚠ 9.1b WHAT A ROW COSTS, AND WHY THE CADENCE IS A POLICY  *(Edwin: "not quite sure how much the evaluation costs and if really every 1 or 2 frames the evaluation should be done")*

The **frame decode is paid anyway** — gamma-decoding the ROI band into a column array already happens
once per frame in today's burst path. ⇒ what a row *adds* is only:

```
   window mean over 50 x 2600 floats  +  C1 rejection  +  Absorption + despike + 3 band means
```

— order **milliseconds**, against a frame period of **~700 ms**. ⛔ **But that is an estimate, not a
measurement**, and this project does not ship estimates: **R1 prints a per-row timing line**, and the
budget is fixed here in advance:

```
   row cost  <  10 % of the frame period   ->  ⭐ evaluate every frame
             >= 10 %                        ->  raise evaluateEveryNFrames (2, 5, ...)
```

⭐ **If it ever bites, drop the CADENCE — never the window.** `W` is the statistics; the cadence is only
how finely the curve is sampled, and at 5-frame cadence the rows are still ~3.5 s apart, far denser than
anything the read rules need.
⛔ **Do not "optimise" with a running sum** (add the new frame, subtract the old). C1 re-judges which
frames are outliers on every window, so the incremental sum is not equal to the reduce it replaces — it
would be a silent divergence from the bench number, for a saving that §9.1b says is not needed.

### ⛔ 9.2 WHAT IT DOES NOT BUY — say this before the benefits

A rolling mean gives **the same information, re-phased.** Consecutive rows share 49 of 50 frames, so
they are not 50 independent measurements:

| | |
|---|---|
| noise per row | **unchanged** — sd ≈ 0.063 `Q%`, the same as one block capture (§16.36.6) |
| independent rows in an arc | **span ÷ window**, i.e. a 10-min arc still holds ~17 independent points |
| ⛔ what must never be claimed | "1200 samples, so σ/√1200" — the frames are shared and the noise is correlated |

⇒ ⭐ **Buy it for the phase, the latency and the lag correction — never for the precision.**

### ⭐ 9.3 THE ONE CORRECTNESS DETAIL — stamp the window at its CENTRE

A boxcar of `N` frames lags the truth by `(N−1)/2` frames. At the ELP's **~1.0–1.5 fps at 2592**
(`CaptureBackend`) that is **17–25 seconds**. Stamp a row at its last frame and every slope, every
vertex and every zero-dose intercept is displaced by that much — a systematic error, not noise.

```
   t_row  =  (t_first + t_last) / 2          ⭐ exactly unbiased for a linear trend
                                             ⚠ second-order error only where the curve bends
```

**Is a 50-frame window short enough?** Compare what it smooths against the floor it must respect:

| process | change across one 35 s window | vs the 0.063 no-re-seat floor |
|---|---|---|
| photodamage ramp, +1.0…1.6 `Q%`/h | **0.010–0.016 units** | ~¼ of the floor — ⭐ invisible, harmless |
| beam clearing, τ ≈ 5 min | small against its own 97 % fall | ⭐ harmless |
| ⛔ bath re-clouding / the first seconds after insertion | **comparable to the window** | ⛔ smeared — shorten the window |

⇒ **the window is a policy value, not a constant**, and because the ring keeps raw frames, a run can be
re-windowed *after the fact*. ⭐ Diagnostics therefore persist per-frame spectra (`.npz`, ~10 MB for a
20-min run); the product persists only the trajectory (§9.7).

### ⭐ 9.4 THE DOSE ACCOUNTING — free today, expensive the day the shutter lands

> ⭐ **"Shutter", since it is used throughout §16.36 without ever being defined**  *(Edwin asked,
> 2026-08-16)*: a blocker — mechanical flap, or simply **switching the LEDs off** — between the lamp and
> the sample, so the sample is lit **only while frames are being taken** instead of continuously. It is
> the obvious cure for photodamage: ~2 s of light per capture instead of the whole session. ⛔ And
> §16.36.7 found it cannot be built on its own, because the lamp's heat is what holds the sample above
> its cloud point — shutter the lamp and the sample re-clouds. ⇒ **shutter ⇒ heated holder (§7)**, which
> is why §11 gates both.

```
   NOW          lamp always on   ->  dose = (jar in beam) x time      frames are FREE
   WITH SHUTTER dose = shutter-open time                              frames COST dose
```

⇒ the loop's **schedule must be a policy**: `CONTINUOUS` today; `DUTY_CYCLE(open = N frames, every T)`
once §7's heated holder + shutter exist. **Same ring, same evaluator, same state machine** — only the
schedule changes. ⛔ Do not hard-code a `while True: read()` loop anywhere; that is the line that would
have to be found and rewritten in three places later.

### ⭐ 9.5 REDUCE SPECTRA FIRST, THEN COMPUTE THE METRIC — never the other way round

`Q%` is a **ratio**, so `mean(Q%)` ≠ `Q%(mean spectrum)`. The shipped bench number is `Q%` of a
60-frame **mean spectrum**. ⇒ a live row must be computed the same way, or the monitor and the bench
disagree by construction — the §10.1a mistake, one level up.

```
   window frames -> MeanOp (C1 dim-frame rejection, already implemented) -> AbsorptionOp
                 -> the plugin's own despike -> the plugin's own band means -> Q%
```

⚠ Per-frame scalars may still be logged, but they are a **diagnostic stream** (frame-to-frame scatter,
dropped-frame rate), never the answer stream.
⚠ C1 judges a frame against its neighbours, so on a rolling window a borderline frame flickers in and
out of the mean. Harmless for the value; report `nAccepted` per row so a run where it collapses is
visible rather than silent.

### ⭐⭐ 9.6 THE REAL REASON — the water bath SHORTENS the clearing phase, and the read rule must be discovered

⛔⛔ **A CORRECTION TO THIS SECTION'S FIRST DRAFT, AND IT IS EDWIN'S**  *(2026-08-16)*:

> *"it is at least the assumption that the water bath pre-clears the sample such that it SEEMS to be
> clear by eye — but this does not mean that it would not clear more afterwards."*

⭐⭐ **"Clear by eye" and "`A_valley` flat" are not the same statement, and the difference is exactly the
signal.** The eye sees large-particle scattering, which dies first; `A_valley` fell **97 %** in the beam
(0.9455 → 0.0257, §2.1) and the tail of that fall lives well below anything visible. ⇒ a bath-cleared
jar may still be clearing when it enters the beam, and **the instrument, not the operator, decides.**

⛔ **So the first draft's two-mode table was wrong** — it let the *protocol* pick the read rule. The
rule is picked by **what the gate observed**, which also answers Edwin's second point: *"the algorithm
should also work if one inputs a muddy sample."*

```
   ⭐ ONE ALGORITHM. The gate ALWAYS runs. What it SAW selects the read:

   frames -> rows -> gate on |ΔA_valley| < 0.005, twice running
                        │
                        ├─ A_valley fell materially before flattening   -> ⭐ the fill was CLEARING
                        │     -> read the VERTEX (§2.2); a minimum exists to find
                        │
                        ├─ A_valley was flat from the first rows        -> ⭐ the fill arrived CLEAR
                        │     -> read the FIRST SETTLED WINDOW (§9.6a); there is no minimum
                        │
                        └─ A_valley never flattens                      -> ⛔ NO ANSWER (§2.5's new guard)
```

⚠ **"Materially" needs a number before R1 ships**, and the honest default is the one already in hand:
a fall larger than the gate's own threshold accumulated over the pre-gate rows, i.e.
`A_valley(first) − A_valley(gate) > 0.005 × gateConsecutive`. ⭐ Whatever the number, it is **logged with
the measurement** — which branch fired is part of the record, because it changes what the value means.

⇒ **§2.3's zero-dose extrapolation stops being a footnote** wherever the second branch fires: the model
risk that made it a footnote ("it assumes the damage rate during clearing matched the rate after") is
proportional to how much clearing there was. To extrapolate back to insertion you need dense, low-lag
samples in the first minute, where block sampling gives you **one point**. That is the ring buffer's
actual job.

#### ⭐ 9.6a And for the arrived-clear branch, the arithmetic says do something simpler still

The ramp is 1.0–1.6 `Q%`/h:

| arc | damage accumulated | vs floors (0.063 no-re-seat / 0.21 refill) |
|---|---|---|
| 1 min | 0.017–0.027 | ⭐ under a third of the no-re-seat floor |
| 2 min | 0.033–0.053 | ⭐ still under it |
| 10 min | 0.17–0.27 | ~1 refill floor — fittable, but you paid for it in dose |

⇒ ⭐⭐ **When the gate says the fill arrived clear, the answer is the FIRST SETTLED WINDOW — and no
extrapolation is needed at all**, because the bias it would remove is smaller than the floor it lives
on. The fit is worth running only in DIAGNOSTIC mode, where the *rate itself* is the object of study
(§11).
⛔ **CORRECTED, 2026-08-17: that is ~2 minutes, not the "~35 s" this section first claimed** — the gate
needs **three** non-overlapping windows before it can fire. §14.2a prices it properly.

| ⛔ NOT a mode the operator selects | ⭐ a STOP RULE the gate's own finding selects |
|---|---|
| arrived clear | first settled window, then **stop** — ⚠ **~2–2.5 min**, not the "~1 min" first written here (§14.2a) |
| was clearing | vertex (§2.2), then stop on a confirmed rise — as long as it takes |
| never flattened | ⛔ no answer, and say which one it was |
| **diagnostic** *(a real mode, chosen by the operator)* | ignore the stop rule, run the fixed arc, keep the whole trajectory + fitted slope + intercept |

⚠ Every branch records the trajectory it saw — "this fill was already clear" must be **evidenced**, not
asserted, or §2.5's new guard cannot fire and §2.4's clearing time has nothing to log.

### 9.7 What is persisted

⇒ ⭐ **superseded by §15**, which specifies it in full (the answer's spectrum goes where a spectrum
always went; a `MonitorRecord` carries the decision beside it; raw frames stay in diagnostics).

---

## ⭐⭐ 10 · THE SHARED OBJECT — how the script and the plugin get the SAME algorithm

> Edwin's constraint, and it is the right one: *"i want the diagnosis script to not repeat itself, so
> things should be implemented with the plugin and the script in mind."* ⭐ The precedent is §10.1a — a
> diagnostic that transcribed the app's constants silently stopped agreeing with it. **This is the same
> failure one level up: a transcribed ALGORITHM.**

### ⭐ 10.1 A PUSH API — the caller owns the loop and the clock, the monitor owns the state

```
   monitor.offer(frameSpectrum, timestamp)  ->  Row | None      ⭐ the whole seam
```

#### ⛔⛔ 10.1a A REDESIGN — the plugin OWNS the monitor; nothing calls INTO the plugin  *(Edwin, 2026-08-17: "everything has to be driven by the plugin … Q% is defined by the plugin so it cannot be consumed by the plugin via plugin.monitorMetrics()")*

⭐ **The objection is right and the first diagram deserved it.** It drew the SDK as a framework that
reaches into the plugin for `Q%` every frame — the plugin demoted to a service the machinery calls.
⛔ Q% is the plugin's own definition; the machinery has no business asking for it.

⭐⭐ **THE FIX — the plugin CONSTRUCTS a monitor and hands it over. The host only feeds it frames.**

```
   plugin.createMonitor(reference)  ->  Monitor        ⭐ the plugin builds the algorithm object
   monitor.offer(frameSpectrum, t)  ->  Row | None     ⭐ the host only pumps frames into it
```

⇒ **there is no host→plugin call in the loop at all.** The host holds a handle it was *given*; whatever
that object does is the plugin's business. ⭐ This is the codebase's existing shape, not a new one: the
plugin already builds `EvaluationResult` view-models and `WorkflowPolicy` and hands them over, and the
host renders/obeys them without knowing what is inside.

#### ⭐⭐ 10.1a-bis COMPOSITION, NOT INHERITANCE  *(Edwin, 2026-08-17: "inherit or use — i would favour composition over inheritance")*

⭐ **Agreed, and it is the stronger form of the same fix.** A base class would hand the plugin an
`offer()` it cannot escape; composition hands it **parts it assembles**, and lets it throw them away.

```
  ┌── the PLUGIN — owns the algorithm, ASSEMBLES the object, and could refuse the parts ──────────────┐
  │                                                                                                   │
  │   createMonitor(reference):                                                                       │
  │       return MonitorEngine(                       ⭐ an SDK part the PLUGIN instantiates           │
  │           ring      = FrameRing(window=50, retention=60),        ⭐ another one                    │
  │           evaluator = self.__clearingEvaluator(reference))       ⭐ ITS OWN object, injected       │
  │                                                                                                   │
  │   ClearingEvaluator — the plugin's own class, inherits NOTHING                                    │
  │       evaluate(windowSpectrum) -> Row      its despike, bands 448-460/500-560/565-580, its Q%     │
  │       decide(rows)             -> Decision its gate 0.005 x2, its read rule, its stop rule        │
  │       coach(rows)              -> str      its wording                                            │
  │   ⛔ owns NO loop, NO camera, NO Qt.                                                               │
  └───────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                              │  hands the assembled object over, ONCE
                                              ▼
  ┌── MonitorEngine ── core/plugin_sdk. ⭐ A PART, not a framework ───────────────────────────────────┐
  │   MECHANICS ONLY: the ring · window(W) · MeanOp+C1 reduce · centre timestamp                      │
  │                  · promote the best spectrum · cadence · the trajectory                           │
  │   offer(frame, t):  ring.add -> if due: reduce -> evaluator.evaluate(...) -> evaluator.decide(...)│
  │   ⛔ knows NO wavelength, NO "valley", NO Q%, and ⛔ NOT the word "plugin" — only the evaluator     │
  │      interface it was HANDED by whoever built it.                                                 │
  └───────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                              │  Row per offer(), MonitorResult at the end
                              ┌───────────────┴───────────────┬─────────────────────┐
                              ▼                               ▼                     ▼
                  clearing_time_course.py             the bench / wizard        test / replay
                  while backend.read():               frameProvider pump        synthetic / .npz
                      monitor.offer(f, t)                                       ⭐ same object, no rig
                  ⛔ NONE of these know what a Row means — they print it, plot it, or assert on it.
```

⭐ **Read it for what is NOT connected:** the host never calls the plugin during a run, the SDK never
names a wavelength, and the plugin never owns a loop.

⚠ **The honest part.** At runtime the engine still calls `evaluate()` — that arrow does not disappear.
What changes is **who names and who constructs**: the SDK no longer knows a class called `plugin` or a
method called `monitorMetrics`; it holds a collaborator it was handed. ⭐ And the plugin gains an exit
inheritance would have denied it: **return your own object instead.** The host's contract is two methods
(§10.2a), not a class — so a plugin that wants a completely different acquisition writes one and the
engine is simply never used.

⭐ Three further things composition buys, all of them concrete: the ring can be swapped for a replay ring
without touching the evaluator; the engine can be unit-tested with a **fake evaluator** (proving it holds
no oil knowledge); and the evaluator can be tested with **no ring at all**.

#### ⚠ 10.1b THE ONE THING THE PLUGIN CANNOT OWN — and why `offer()` is still a push

"Driven by the plugin" has to stop at the loop, and the reason is mechanical, not philosophical:

| owns the camera | the host (a video thread) — ⛔ never the plugin |
| --- | --- |
| owns the Qt event loop | the host — ⛔ a plugin-side `while` would freeze the GUI for the whole run |
| owns the clock | the caller — ⭐ which is what makes replay from `.npz` exact, with recorded timestamps |
| owns **everything else** | ⭐ the plugin: what a row is, when it is settled, which row wins, when to stop, what to say |

⇒ the plugin drives **what happens**; the host drives **when a frame arrives**. ⛔ Any design where the
plugin pumps frames itself needs three different pumps (script / GUI / replay) and blocks the GUI in
one of them.

⛔ **Not a pull API.** A monitor that calls a frame provider itself would have to own threading, the
clock and the stop condition — and then the script, the bench and a replay-from-file each need a
different one. With `offer(...)` all three keep the loop they already have:

| caller | its loop | what it does with a Row |
|---|---|---|
| `diagnostics/clearing_time_course.py` | `while backend.read()` | prints it, appends it to the CSV |
| the bench / wizard host | the existing `frameProvider` pump (§9.1 of the convergence spec) | coach line + live plot |
| a unit test | a synthetic clearing+damage curve | asserts the gate fires at the right sample |
| ⭐ replay | frames from a run's `.npz`, with their recorded timestamps | regression-tests the algorithm on 2026-08-14 |

⭐ Passing the timestamp IN (rather than reading a clock inside) is what makes replay exact.

### 10.2 Where each piece lives — PARTS in the SDK, assembly and behaviour in the plugin

```
   spectracsPy-core / plugin_sdk / acquisition /
       FrameRing.py       a part: bounded ring of raw frames; window(k) -> Spectrum carrying k frames
       MonitorEngine.py   a part: offer(), the reduce, the centre stamp, the best-spectrum promotion,
                          the cadence, the trajectory. ⭐ Composed with a ring and an EVALUATOR.
       BurstEvaluator.py  ⭐ the default evaluator — "no intermediate evaluation" (§10.6)
       MonitorPolicy.py   ⚠ mechanical knobs only: W, retention R, minWindow, cadence,
                          schedule (CONTINUOUS | DUTY_CYCLE), maxMinutes
                          ⛔ NO gateOn, NO thresholds — those are the evaluator's, i.e. the plugin's

   the PLUGIN supplies
       createMonitor(reference) -> Monitor        ⭐ it ASSEMBLES: engine + ring + its own evaluator
                                                  ⚠ default in the SDK returns the plain burst (§10.6)
```

#### ⭐ 10.2a THE HOST'S ENTIRE CONTRACT — two methods, no class

```
   offer(frameSpectrum, timestamp) -> Row | None      ⭐ duck-typed. NOT a base class, NOT an ABC.
   result()                        -> MonitorResult
```

⇒ `MonitorEngine` is merely the **most convenient** thing that satisfies it. ⛔ Nothing anywhere requires
a plugin to use it.

⛔⛔ **THE `gateOn="valley"` STRING IS GONE, AND GOOD RIDDANCE.** The first draft had the SDK gate on a
*named scalar* looked up in a dict — stringly-typed indirection whose only purpose was to let the
framework run a decision it does not own. With `decide()` on the plugin's own evaluator, the gate is just
**code in the class that owns the numbers**, and `0.005`, `×2`, `12–22`, `0.15`, `448–460` never leave
`DevSpectralPlugin`.
⚠ `MonitorPolicy` survives **only** for W / R / cadence / schedule — the things that are genuinely about
buffering rather than about oil. ⭐ If even those want to be per-plugin, they are constructor arguments
the plugin passes and the class disappears.

### ⭐⭐ 10.3 THE DRY KEYSTONE — one public metric method, and it deletes an existing wart

`clearing_time_course.py` today reaches into the plugin through **name mangling**:

```python
   plugin._DevSpectralPlugin__despikedAbsorption(absorption)     # ⛔ private
   plugin._DevSpectralPlugin__vTerms(despiked)                   # ⛔ private
```

That is the DRY instinct fighting the absence of an API. ⇒ **promote exactly that pair to one public
method on the plugin** — `monitorMetrics(container) -> {"qPercent", "soret", "valley", "qBand", "dn"}`.

⚠ **And note who calls it, because §10.1a is the whole point:** the plugin's own `evaluate()` calls it,
and a script may call it directly for a one-off pair. ⛔ **The SDK never calls it** — it does not know
the method exists. The plugin is not being asked for `Q%` by the machinery; it computes `Q%` for itself,
inside an object it built, and emits a `Row` the machinery merely carries.
⭐ The script stops using private names not by discipline but because it no longer needs to.

### 10.4 The host adapter, and what does NOT move

| | |
|---|---|
| `SpectralWorkflowEngine.captureMonitoredStep(step, frameProvider, onRow)` | app tier, **thin**: asks the plugin for its monitor **once**, then pumps the provider, decodes each frame, calls `offer()`, returns `{bestSpectrum, bestRow, rows[], outcome, clearingSeconds}` |
| ⛔ the algorithm | ⛔ **not** in the engine — the engine imports Qt (`qGray`), the monitor must stay Qt-free per `SPEC_project_structure.md` |
| `captureAcquisitionStep` | ⭐ **becomes one line over the same machinery** — see §10.6; a plugin that declares nothing gets exactly today's behaviour |
| `MeasurementStep(role, label, frames)` | ⭐ per-STEP: the plugin decides which step gets which evaluator (the SAMPLE step clears; the REFERENCE step does not) |
| the reference | captured once, held fixed, passed into the monitor — every row is `S_window` against that one `R` |

### ⭐⭐ 10.6 THE PLUGIN THAT NEEDS NO INTERMEDIATE EVALUATION — the burst IS the degenerate monitor  *(Edwin, 2026-08-17: "if a plugin does not need such an intermediate evaluation … how would that be in harmony with the monitor thing?")*

⭐⭐ **The right answer is not an opt-out flag. It is that there was only ever one thing.** Today's block
capture — grab N frames, mean them, done — is a monitor whose evaluator says *"no opinion; stop when the
window is full"*:

```
   BurstEvaluator                       (ships in the SDK, ~10 lines)
       evaluate(window) -> Row(spectrum only, no metrics)   ⭐ no metric at all
       decide(rows)     -> STOP once nAccepted >= N         ⭐ no gate, no read rule
       coach(rows)      -> ""                               ⭐ nothing to say
```

⇒ **one code path in the host, for every plugin.** The host always pumps frames into a monitor; what
differs is only which evaluator the plugin put inside it.

| the plugin | what it writes | what it gets |
|---|---|---|
| measures something already dissolved | ⭐ **nothing at all** | today's N-frame burst, byte for byte |
| wants a live preview but no decisions | an evaluator with metrics + `decide -> CONTINUE` | rows to plot, same stop |
| pumpkin oil | `ClearingEvaluator` | §9.6's gate, read rule and stop |

⭐ **And the concept stays invisible to the plugin that does not want it** — that is the harmony test,
and it is the criterion this section is written against: no new hook to implement, no flag to set, no
"monitored" boolean on the step. The default is in the SDK, not in every plugin.

⚠ **Two things this must not become.**
⛔ **Not a big-bang refactor of the shipped capture path.** R1 builds the engine; a test proves
`MonitorEngine + BurstEvaluator` returns **the identical spectrum** to today's `__runBurst` for the same
frames; only then does `captureAcquisitionStep` delegate. ⭐ If that equivalence test fails, the two
paths stay separate and nothing is lost.
⚠ **The C3 top-up rule must survive the merge** (§`__runBurst`: keep grabbing until N frames *survive*
C1). In the unified form that is `BurstEvaluator.decide` counting `nAccepted`, not frames offered —
which is the same rule, expressed where it now belongs.

### ⭐⭐ 10.7 CAN THE DIAGNOSTIC SCRIPT DRIVE THE REAL PLUGIN? — yes, in ~15 lines  *(Edwin, 2026-08-17)*

```python
    context   = _appContext() or calibrationFromServerDb()
    backend.open(deviceId=..., whiteBalanceKelvin=6500);  exposure = _pickExposure(backend)   # ⭐ the SCRIPT's job
    reference = captureMean(backend, roi, coefficients, frames)

    monitor = DevSpectralPlugin().createMonitor(reference)      # ⭐⭐ THE REAL PLUGIN. No copy of anything.
    while not monitor.isFinished():
        image = backend.read()
        if image is None:  continue
        row = monitor.offer(frameSpectrum(image), time.time())  # ⭐ the plugin's gate, read rule and stop
        if row is not None:  print(row); csv.writerow(row)
    result = monitor.result()
```

⭐ **Nothing in that loop knows what `Q%` is** — which is the §10.1a-bis boundary, now paying for itself:
the script measures **the algorithm the bench runs**, not a transcription of it.

#### ⭐ 10.7a WHAT STAYS THE SCRIPT'S OWN, DELIBERATELY

| the script owns | because |
|---|---|
| the camera: device, WB, ⭐ **exposure pinned for the whole run** (`_pickExposure`, then frozen) | ⛔ auto-exposure would compensate the very clearing being measured (§16.7). The bench does its own AE sweep and **must**; the diagnostic must not |
| the clock, the CSV, the plots, the prompts | it is an instrument for a human at a bench |
| calibration bootstrap from the server DB | it must run with the app closed |

⇒ ⭐ **the script owns the CAMERA; the plugin owns the MEANING.** That line is the whole answer.

#### ⛔⛔ 10.7b THE HOLE THIS QUESTION EXPOSED — the divergence is BELOW the metric seam, in the PIXELS

⛔ **Identical algorithm + identical metric still gives different numbers today, because the two sides
reduce the ROI band differently:**

| | inset (rows dropped top and bottom) | keeps |
|---|---|---|
| the app — `ImageSpectrumAcquisitionLogicModule` | **1/3** *(Edwin, 2026-08-06: "take the filet piece")* | the middle **33 %** |
| `diagnostics/_spectrum(...)` | **0.2** | the middle **60 %** |

⚠ And that gap is **deliberate for the OLD diagnostics** — the module's own comment says
`reference_drift_probe.py` and `reduction_sum_vs_max.py` hardcode 0.2 *on purpose*, to keep reproducing
the numbers they published. ⛔ **Do not repoint those.**

⭐⭐ **But the settling script is NEW, and it must not inherit the gap.** Its frames go into the plugin's
own monitor and its rows are meant to equal bench rows. ⇒ **it calls the app's own per-frame extraction**,
which needs exactly one setup step the script does not do today:

```
   install a SpectrometerProfile (roi + cubic) into ApplicationContextLogicModule
   — the ~8 lines SpectralWorkflowEngine.__ensureCalibration already runs —
   because ImageSpectrumAcquisitionLogicModule reads its calibration from that singleton,
   not from arguments.
```

⚠ **Two caveats, recorded rather than resolved:** that module is **app-tier and imports Qt**, so "the
monitor is Qt-free" remains true while "the whole capture chain is" does not — it matters for Android,
not for the desktop bench. And a run made with inset 1/3 is ⛔ **not comparable frame-for-frame** with
the 2026-08-14 archive made at 0.2; the replay corpus must record which inset produced it.

#### ⭐ 10.7c DOES THE SCRIPT STILL SEE `Q%`? — yes; the Row IS the values  *(Edwin asked, 2026-08-17)*

⭐ **Nothing is hidden from the script.** `offer()` returns the plugin's **own** `evaluate()` output:

```
   Row   t              ⚠ the WINDOW-CENTRE stamp (§9.3), not the moment the line is written
         values         {"qPercent": 14.07, "soret": 0.612, "valley": 0.0271, "qBand": 0.078,
                         "dn": 31.4, ...}          ⭐ exactly today's printed columns
         n, nAccepted   frames in the window / surviving C1
         provisional    True while the ring is still filling (§14.2)
```

⛔ The **SDK** does not interpret those keys — the **script** may, and should. It is a diagnostic *for
this plugin*; pretending otherwise would be ceremony. ⭐ Recommended split: the **CSV header from the
declared `columns`** (§15.2), so a new plugin column appears automatically; the **console table by
name**, because fixed-width columns need a fixed layout.

**⚠ "every x time units" — the two traps:**

| ⛔ don't | ⭐ do |
|---|---|
| re-average rows onto a coarser grid | rows are **already window means**; averaging overlapping windows makes the effective window ambiguous — and it is §3's "never average across the curve" |
| write only every x-th row and lose the rest | ⭐ **CSV gets EVERY row** (~1700 over 20 min, a few hundred KB — it is the record); the **console prints every x seconds** so a human can read it |

⭐ If fewer rows are genuinely wanted, the honest knob is the **cadence** (`evaluateEveryNFrames`) — then
one row still equals one written line, and nothing is resampled after the fact.

⚠ **Two columns the old CSV did not need:** `n` (a 20-frame provisional row must never be read as a
50-frame one) and both timestamps — ⛔ `Row.t` is the window CENTRE and lags the last frame by 17–25 s,
so a reader who assumes it is "when the line appeared" mis-times every event by half a window.

⭐ **The `.npz` stays the script's own business** — it already holds the frames before it offers them, so
the monitor never needs to expose spectra at all.


### 10.8 Phasing (slots into §6)

⭐⭐ **ORDER SET BY EDWIN, 2026-08-17 (§11.9): the plugin is built BEFORE the experiment**, because the
settlement algorithm is needed at capture anyway and §11 should measure the protocol the instrument will
actually use. ⇒ the earlier "run §11 first on the existing script" is the **fallback**, not the plan.

| PH | deliverable | gate |
|---|---|---|
| ⭐ **R0** | **cancel + the hard caps (§12) on the EXISTING burst** | a 60-frame capture can be stopped mid-run; `maxSeconds` cannot be `None`. ⭐ A 20-minute §11 arc makes this load-bearing, not a nicety |
| **R1** | `FrameRing` + `MonitorEngine` + `BurstEvaluator`, headless, plus the plugin's own `ClearingEvaluator` + public `monitorMetrics()` | ⭐ **two tracks, both runnable today (§11.9b)**: `decide()` replayed on the 2026-08-14 **CSV rows** fires at t ≈ 16.7 and reads 13.27; and `BurstEvaluator` reproduces `__runBurst` **exactly** (§10.6). ⭐ A fake evaluator proves the engine holds no oil knowledge |
| **R2** | `clearing_time_course.py` rewritten onto the plugin (§10.7) — same CLI, same CSV, **+ `--npz`**, ⭐ + the diagnostic stop policy (run the full arc past the read) | its own baseline CSV re-derives the same verdict; ⛔ the private-name access is gone; the latch (§14.6) is unit-tested — a late noise dip must NOT become the answer |
| ⭐ **R3** | ⭐⭐ **the §11 experiment, on R2, 20-minute arcs** | see §11.9d |
| **R4** | `captureMonitoredStep` + the legend box (§13.2) + the indeterminate status bar | click-through |
| **R5** | persistence (§15: the generic `MonitorRecord`) + the "never cleared" outcome | a saved run can be re-examined |
| **R6** | ⭐ `SeriesPlotView` — built **once**, used three times: the live trace (§13.2), the **Settling step-tab** (§18) and the PDF page | click-through + a report render; ⚠ costs two renderers (screen + matplotlib) |

⚠ **R1 before R3, and R3 before R4.** The experiment needs the maths, not the GUI; shipping the GUI
first would mean tuning a legend box against an algorithm whose read rule §11 might still change.
⭐ **R2 is the smallest step that unblocks the experiment** — no host, no persistence, no UI.

⚠ **UI note:** rows arriving at ~1.4 Hz, each jittering ±0.06, will look alarming if printed live.
The coach line shows the **state** and a value refreshed every ~5 s; the plot shows the trajectory.

---

## ⭐⭐ 11 · THE HEAT-DOSE EXPERIMENT — does warming the sample damage it?  *(Edwin, 2026-08-16)*

> **Status: PROTOCOL, pre-registered. Not yet run.** §16.36 established that **light browns** and
> **heat clears**. It did **not** establish that heat is innocent — it only never had a way to look.
> Edwin now has a repeatable bath, so heat dose can be varied with light dose held fixed.

### ⭐⭐ 11.1 WHY THIS IS NOT A CURIOSITY — it is the gate on the heated holder

§7's heated holder does not warm the sample for 30 seconds. It holds it at ~50 °C **for the whole
measurement, every measurement**. And §16.36.7 showed the shutter *requires* the heated holder.

```
   heat is innocent      ->  ⭐ the bath can be used freely, §7 is de-risked, the shutter stays possible
   heat damages          ->  ⛔ the heated holder is dead, and the shutter dies with it;
                             the bath needs a TIME LIMIT written into the protocol
```

⇒ arm (b) — 5 minutes at 52 °C — is deliberately **the exposure a heated holder would impose**.
⭐ It also answers a second live question for free: whether a jar may be **re-warmed and re-measured**,
which decides whether σ_fill runs may re-use a fill (§16.34.3).

### 11.2 The recipe, as operated  *(Edwin's, 2026-08-16 — the numbers are his)*

```
   hotplate at ~90 C  ->  glass of water reaches ~52 C  ->  jar in, ⭐ LID CLOSED  ->  CLEAR in ~30 s
   ->  jar out, dried on a paper handkerchief  ->  ready to measure
```

⭐ **The lid is closed** *(Edwin, 2026-08-16)* — so no bath water in and no IPA out (§11.7).
⛔ **"Clear" here means clear TO THE EYE**, which is not the same as `A_valley` flat — see §9.6. It is
the instrument's job to decide whether the fill really arrived settled, and this protocol does not
assume it did.

⚠ Faster than §16.36.7's "~2 min at 50 °C" because the plate keeps driving the bath. ⇒ record the bath
temperature per arm; **the variable is temperature, not the plate setting.**

### 11.3 The arms — and the fourth one is not optional

| arm | treatment | what it isolates |
|---|---|---|
| **a** | 30 s at 52 °C — just enough to clear | the minimum heat that makes a measurement possible |
| **b** | **5 min** at 52 °C | ⭐ heat DURATION, ≈ the heated holder's exposure |
| **c** | clear → let it re-cloud at ambient (~8 min) → re-clear; ⭐ **×5** *(Edwin, 2026-08-16)* | thermal CYCLING + re-measurability |
| ⚠ arc | ⭐ **20 minutes, identical in every arm** *(Edwin, 2026-08-17 — §11.9d)* | `Q%(t₀)` from the latched read at ~2 min **and** the photodamage slope from the tail, in one run |
| ⭐ **d** | sits the same total elapsed time as **c**, in the DARK at room temperature, then 30 s at 52 °C at the end | ⛔ the control Edwin's list is missing — ⚠ **open, to be decided** |

⛔ **Without (d), arm (c) cannot be read.** ⭐ At five cycles that is **~45–50 minutes** of elapsed time
(≈8 min re-clouding + ~30 s re-clearing, five times), during which the dilution also simply *ages* in the
dark. Any change in (c) would be cycling **and** elapsed time, inseparable — and at 45 min the elapsed
term is now the *larger* suspect, not the smaller one.
⚠ (d) covers (b)'s smaller version of the same confound (5 min vs 30 s of elapsed time) as well.
⚠ **Five cycles also costs the most light of any arm** if the jar is measured between cycles — so it is
not, unless the run explicitly wants that. ⇒ **cycle in the dark, measure once at the end**, exactly like
the other arms, or the light dose stops being held fixed and the experiment loses its one control.

⭐ **One dilution, aliquoted into four jars at t = 0.** ⛔ Not four dilutions — that puts σ_fill (0.21)
between the arms before the experiment starts.

### 11.4 The readout — four numbers per arm, all from one monitored run

Each arm: insert, run the monitored acquisition (§9) for a **fixed 10-minute arc**, identical for all four.

| | reads out |
|---|---|
| `Q%(t₀)` — intercept of the fitted damage line | ⭐ **the heat effect itself** |
| `slope` (units/h) | ⭐ did heat **sensitise** the sample to light? |
| `A_valley(t₀)` | ⭐ free answer to §16.36.7's open question: is a bath-cleared fill as clear as a beam-cleared one? |
| SNV shape distance `D` vs arm (a) (`SPEC_history_tracker.md`) | scaling vs **chemistry** — a real change moves the shape, a nuisance does not |
| the band-fall ratio (§16.36.1) | which of the two processes any movement belongs to |

### ⭐⭐ 11.5 THE DECISION RULE — fixed before the run, per §16.34.3's habit

```
   |Q%(t0)_b - Q%(t0)_a|   <  0.21  (one refill floor)  ->  heat duration is NOT a material damage term
                           >= 0.21                      ->  it is; the bath gets a time limit and §7 is in doubt
   |slope_b - slope_a|     <  0.3 units/h               ->  heat does not sensitise the sample to light
   arm c vs arm d          same test                    ->  cycling is (or is not) worse than merely waiting
```

### ⛔ 11.6 WHAT ONE JAR PER ARM CAN AND CANNOT CONCLUDE

The four jars are different fills, so the floor between arms is the **refill floor, 0.21** — not the
0.063 no-re-seat floor.

| | |
|---|---|
| n = 1 per arm | ⭐ detects a **large** effect (≳ 0.4–0.6 units). One evening, four jars — worth doing first |
| ⛔ a null result at n = 1 | is a **BOUND** ("no effect larger than ~0.5 units"), ⛔ **never** "heat is safe" |
| n = 3 per arm (12 jars) | SE ≈ 0.12 ⇒ resolves ~0.3 units — the run to do *only if* the screen shows nothing and the bound is not good enough |

⇒ ⭐ **Stage it: screen at n = 1, then decide.** Against a photodamage term of 1.0–1.6 units/h, a heat
effect worth worrying about would be visible in the screen.

### ⚠ 11.7 THE CONFOUNDS THAT MUST BE CONTROLLED, NOT ASSUMED AWAY

| ⚠ | control |
|---|---|
| ~~**IPA evaporation**~~ — ⭐ **RESOLVED: the lid is closed in Edwin's bath already** *(2026-08-16)*, so neither solvent out nor bath water in | ⭐ keep the ⭐**DN as a free witness** anyway — same dilution, drifting DN ⇒ the seal failed. It costs nothing and turns an assumption into an observation |
| **entry temperature differs** — (b) enters fully equilibrated at 52 °C, (a) at maybe 45 °C | compare late rows (after ~2 min, both relaxed toward the holder's ~40 °C) **as well as** `t₀`. A hotter jar also convects more — visible as elevated frame-to-frame scatter (§9.5) |
| **water film in `A_valley`** — exactly where the clearing signal lives (§16.36.7) | dry the jar completely; Edwin's handkerchief step, kept explicit. ⚠ And **again just before insertion**: a jar leaving a 52 °C bath into a cooler room re-condenses on the way |
| **re-clouding during transfer** | ⚠ ~1.5 °C/min cooling ⇒ 3–5 min transfer budget; log the delay per arm |
| ⭐ **re-clouding INSIDE the beam** — the holder is cooler than the bath (§14.5) | ⭐ **pre-warm the instrument and keep the lamp on between arms** (§14.5a), or arm (a) meets a cold holder and arm (d) a warm one — a temperature confound in the middle of a temperature experiment |
| **lamp drift + batch ageing across the evening** | reference at the start and at the end (`--reference-at-end`, §16.7 — a **bound**, not a correction); ⭐ counterbalance the beam order (a,b,c,d then reversed on a second batch) |

### ⛔ 11.8 HOW TO RUN IT — ⭐ SUPERSEDED BY §11.9: Edwin chose to build the plugin FIRST  *(2026-08-17)*

> ⚠ **§11.8 below remains valid as the fallback** — it is what to do if the experiment has to happen
> before any code lands. ⭐ **§11.9 is the decision.**

⭐ It is the same script from the last session (the one printing `Q%`, `A_Soret`, `A_valley`, `A_Q`, DN,
`W`), run with its **pauses removed**. ⛔ No ring buffer, no monitor, no plugin change.

```bash
   ./venv/bin/python diagnostics/clearing_time_course.py \
       --label heat_arm_a --minutes 10 --every 0 --frames 60 --npz
                                       └──────┘ ⭐ the ONE change of habit: back-to-back blocks
                                                  (the script sleeps `every` AFTER each capture, so 0
                                                   means "start the next one immediately")
```

At ~1.0–1.5 fps a 60-frame block takes **40–60 s**, so `--every 0` already samples **as fast as the
camera physically allows**. ⇒ ~10–13 rows per arm over 10 minutes.

#### ⭐⭐ WHY THE RING BUFFER WOULD ADD ALMOST NOTHING HERE

| | back-to-back blocks (today) | rolling windows (R1) |
|---|---|---|
| rows per 10 min | ~11 | ~850 |
| ⭐ **INDEPENDENT** rows per 10 min | **~11** | **~14** |
| noise per row | sd 0.063 | sd 0.063 — ⭐ identical |

⇒ ⭐ **the slope and the `t₀` intercept — the whole readout of §11.4 — come out the same.** §9.2 said it
in the abstract; this is the same statement priced for this experiment. The ring buffer buys **latency
and an early stop**, which are *product* properties. §11 is not a product run.

#### ⚠ AND IF THE RE-CLOUDING DIP (§14.5) NEEDS RESOLVING, ROLLING IS THE WRONG TOOL

⛔ A rolling window does **not** un-smear a transient shorter than the window — only a **shorter window**
does. ⇒ if the dip must be resolved, the knob is `--frames 20` (a ~15 s window, ⚠ at sd ≈ 0.11 instead
of 0.063), not "make it rolling".

⭐⭐ **Which is the real reason for `--npz`:** dump the raw per-frame spectra and the analysis window
becomes a **post-hoc choice** — re-window the same run at 20 or 60 frames afterwards, with no second
trip to the rig. ⚠ Record the inset (§10.7b) and the timestamps in the file, or the corpus cannot be
compared with anything.

#### ⭐ 11.8a WHAT `--npz` IS — a proposed new flag, ~20 lines  *(Edwin asked, 2026-08-17)*

⛔ **It does not exist yet, and nothing in `diagnostics/` writes one today** — the archive is CSV.
`.npz` is simply **NumPy's own zipped multi-array file** (`np.savez_compressed`): one file holding
several named arrays, read back with `np.load`. NumPy is already a dependency, so it costs nothing.

⭐⭐ **What it saves is precisely what the script THROWS AWAY today.** `captureMean()` grabs 60 frames,
averages them, and **discards the 60** — the per-frame information exists for a moment and is deleted.

```
   run_20260817_2143_heat_arm_a.npz
       nanometers   (2600,)            the x axis, once
       frames       (660, 2600)        ⭐ EVERY captured frame, linear, in order
       timestamps   (660,)             ⭐ per frame — what makes replay exact (§10.1)
       reference    (2600,)            the reference mean this run was measured against
       meta         inset=0.333, exposure, roi, coeffs, label, frames-per-block, script version
```

⚠ **Size:** ~660 frames × 2600 bins × 8 bytes ≈ **14 MB** per 10-minute arm, less once compressed.
Four arms ≈ 50 MB — ⭐ a non-issue on the bench machine, and ⛔ exactly why the *product* never does this
(§15.3).

**Three things it buys, and only the first is about §11:**

| | |
|---|---|
| ⭐ re-window post hoc | analyse the same run at 20 or 60 frames — the §14.5 dip question answered without a second rig session |
| ⭐⭐ the replay corpus for R1 | feed the frames back through the monitor **with their recorded timestamps** and the algorithm is tested deterministically, on real fills, with no camera |
| ⭐ future metrics on old runs | any metric invented later can be computed on these fills — ⛔ impossible from a CSV of band means |

⚠ It is **additive**: the CSV stays exactly as it is, and every existing report tool keeps working.

---

### ⭐⭐ 11.9 THE DECISION — build the plugin first, and the script runs LONGER. That is the only difference.  *(Edwin, 2026-08-17)*

> *"i think we need the settlement algorithm at capturing anyway, so i would prefer implementing the
> plugin changes first and let the diagnosis script use the plugin. There is only one difference between
> the plugin run and the script run: the script should run longer — even if settlement has been
> detected, say 20 minutes, in order to observe degradation by light."*

⭐⭐ **Endorsed, and the framing is exactly right: one algorithm, two stop rules.** It maps onto a single
policy flag (§9.6's diagnostic row), because `decide()` is where stopping lives.

#### ⭐ 11.9a WHY IT IS THE BETTER ORDER, AND NOT JUST A PREFERENCE

⛔ Running §11 on block sampling and shipping the product on the monitor would measure the heat question
**under a protocol the instrument does not use.** ⚠ §16.36.8 is the whole warning: *the protocol changed
the numbers, and nobody noticed for weeks.* ⇒ ⭐ **measure the final protocol with the final protocol.**

#### ⭐⭐ 11.9b AND IT DISSOLVES A CIRCULARITY I HAD LEFT IN R1

⛔ R1's acceptance test was "**replay 2026-08-14** and reproduce t ≈ 17, `Q%` 13.27" — ⛔ **but no replay
corpus exists**: that run was saved as a CSV of 3-minute band means, not as frames. R1 would have been
waiting on data only R2 could produce.

⭐ **Two test tracks fix it, and neither needs an `.npz`:**

| track | what it proves | data it needs |
|---|---|---|
| ⭐ replay the 2026-08-14 **CSV rows** through `decide()` alone | the gate, the branch, the vertex, the rate conversion (§14.3) — ⭐ **the risky arithmetic** | ⭐ already in the archive |
| ⭐ `MonitorEngine + BurstEvaluator` vs today's `__runBurst`, same frames | the ring, the reduce, C1, C3 — the mechanics | ⭐ synthetic frames |

⇒ **R1 is testable today.** The `.npz` then makes every *future* run replayable, which is a gain rather
than a prerequisite.

#### ⭐ 11.9c THE ONE DIFFERENCE, STATED PRECISELY

```
   product      decide() -> STOP at the read              ~2 min (§14.2a), minimum dose
   diagnostic   decide() -> CONTINUE to a fixed arc       20 min, the ramp is the point
                            ⭐ the ANSWER IS STILL LATCHED at the read (§14.6)
```

⚠ **Two further differences exist but are NOT algorithmic** — they were always the caller's (§10.7a):
the script **pins exposure** (the bench sweeps AE), and the script writes CSV/`.npz` (the product writes
a `MonitorRecord`). ⇒ Edwin's "only one difference" is exactly right *about the algorithm*.
⛔ **Diagnostic mode must be recorded in the run's own record**, so a 20-minute run can never later be
read as a product measurement.

#### ⭐ 11.9d WHAT THE 20-MINUTE ARC BUYS — and the rule it imposes

| arc | damage accumulated (1.0–1.6 `Q%`/h) | vs the 0.063 row noise |
|---|---|---|
| 10 min | 0.17–0.27 | ~3–4× |
| ⭐ **20 min** | **0.33–0.53** | **~5–8×** — ⭐ roughly halves the slope's standard error |

⭐ **And one run now yields BOTH §11 readouts:** `Q%(t₀)` from the latched answer at ~2 min (§14.2a), and the
photodamage slope from the 19 minutes after it.
⛔ **THE ARC MUST BE IDENTICAL IN EVERY ARM.** Different arc lengths mean different lever arms and
different accumulated dose at the end — the arms would stop being comparable in exactly the quantity
being compared.
⚠ Four arms × 20 min ≈ **80 minutes of measurement** plus heating and transfer — a long evening. ⭐ Cancel
(R0) stops being a nicety at that length.

#### ⚠ TWO PRACTICAL GOTCHAS

⚠ The script's printed **`readiness` column will say "warming up" for the whole 10 minutes** — its rule
is the OLD one (drift over the last **15** min against the 0.21 refill floor, §10.5), which cannot fire
inside a 10-minute run. ⛔ That is cosmetic, not a failure: §11 reads the CSV, not that column.
⚠ `--every 0` means the lamp-on-jar time is the full 10 minutes for every arm — ⭐ which is exactly what
the experiment wants (light dose **held equal** across arms) and costs nothing extra, because the lamp
is on regardless (§9.4).

---

## ⭐⭐ 12 · STOPPING — cancel, the hard caps, and the guarantee  *(Edwin, 2026-08-17)*

> *"we need some way to cancel a running measurement … and the algorithm must be bullet-proof in the
> sense that it stops some time."* ⭐ Both are right, and the second one is a **safety property**, not a
> feature: an acquisition that can fail to terminate is an instrument that can hang with the lamp on the
> sample.

### ⭐ 12.1 CANCEL — the host already has everything it needs

```
   the operator clicks Cancel
     -> the click is DELIVERED, because CapturePanel.__pumpFrames already spins a nested QEventLoop
        for ~120 ms per frame: the GUI is live throughout a burst today  (verified, 2026-08-17)
     -> the handler sets ONE flag
     -> the frame provider sees it and returns the CANCELLED sentinel
     -> the engine stops offering, asks the evaluator to finalise, returns outcome = CANCELLED
```

⭐ **Latency is one frame (~0.7 s) and it needs no threading work at all.**

#### ⭐⭐ 12.1a THE CANCEL BUTTON *IS* THE MEASURE BUTTON — relabelled  *(Edwin, 2026-08-17)*

> *"I want the cancel button to be the same as the measurement button, just with a changed label."*

⭐ **Adopted.** No new widget, nothing to lay out at 412 dp (§17/U6), and the control that started the
run is the control that stops it — which is the clearest affordance available.

```
   state        label                              enabled?              style
   ─────────────────────────────────────────────────────────────────────────────────────────
   idle         "Capture reference" / "…sample"    when connected+streaming   normal
   ⭐ capturing  "Cancel"                           ⭐ YES — the ONLY enabled   danger / secondary
                                                      control on the panel
   cancelling   "Cancelling …"                     ⛔ no (≤ 1 frame, ~0.7 s)   dimmed
```

⛔⛔ **TWO EXISTING BEHAVIOURS MUST INVERT, AND BOTH ARE ONE-LINERS THAT ARE EASY TO MISS:**

**1 · `__updateControls()` currently DISABLES the button during capture.**

```python
   busy = self.__autoExposing or self.__capturing
   self.__captureButton.setEnabled(connected and streaming and not busy)     # ⛔ today
   self.__captureButton.setEnabled(connected and streaming and              # ⭐ needed
                                   (not busy or self.__cancellable))
```

⚠ Every *other* control stays disabled exactly as today — the button becomes the single live element.

**2 · `getCaptureButton()` is handed to the ACQUISITION-GUIDANCE cue** (`SPEC_acquisition_guidance.md`),
which paints the amber **▶ NEXT** highlight on it. ⛔ Left alone, a running capture would show a button
labelled **"Cancel"** wearing a highlight that urges the operator to press it. ⇒ ⭐ **the guidance cue
must be suppressed while `__capturing`.**

**The dispatch — and §12.1's re-entrancy rule is what makes it safe:**

```python
   def __onClickedCapture(self):
       if self.__capturing:                     # ⭐ a RE-ENTRANT click, inside the nested event loop
           self.__cancelRequested = True        # ⛔ set the flag and NOTHING else
           self.__setCaptureButtonState(CANCELLING)   # relabel + disable, immediately
           return                               # ⛔ never re-enter the capture path
       ...                                      # the existing capture path, unchanged
```

⭐ **Disabling on the way into "Cancelling …" is what stops a double-click** from either cancelling twice
or starting a fresh capture while the first is still unwinding on the stack below.

⚠ **Cancel during the ~15 s AE sweep too, not only during the burst.** The sweep is the longest single
blocking stretch of a capture (§23/V4) and it already pumps events in its own wait loop — so it can test
the same flag. ⛔ A Cancel that is dead for the first 15 seconds teaches the operator it does not work.

⛔ **No confirmation dialog.** A modal opened from inside a nested event loop is exactly the re-entrancy
this section is avoiding, and the run is cheap to repeat — ⚠ subject to §17/U2's warning that the fill
has already banked dose.
⚠ **Re-entrancy is the only trap:** that click arrives *inside* a nested event loop, on the same stack as
the capture. ⛔ The handler may **only set the flag** — never touch capture state, never start another
capture, never navigate. Everything else stays disabled through the existing `__capturing` guard.

**What a cancelled run leaves behind:**

| | |
|---|---|
| the step's container | ⛔ **untouched** — a cancelled capture is not a capture, and the workflow must not advance on a partial one |
| the trajectory so far | ⭐ kept for inspection, marked `CANCELLED`, and ⛔ never reported as a measurement |
| may a cancelled run still yield a value? | ⭐ **the evaluator decides**, via `result(CANCELLED)` — the default is *no*. The plugin owns what its own half-finished run means |

⭐⭐ **And this covers the plain 50-frame burst too** — which today cannot be cancelled at all. Under
§10.6 there is one code path, so **cancel is implemented once and every plugin gets it**, including the
ones that never asked for a monitor. ⭐ That is the clearest payoff of unifying the two paths.

### ⭐⭐ 12.2 TERMINATION — three layers, and the outer two do not trust the inner one

```
   L1  the evaluator's own stop rule            decide() -> STOP        ⚠ this is the layer that can be buggy
   L2  the ENGINE's hard caps    maxSeconds, maxFrames                  ⭐ ALWAYS on, evaluator cannot disable
   L3  the HOST's no-frame watchdog             no frame for K seconds  ⭐ the engine cannot see this one
```

⛔ **`maxSeconds` may never be `None`.** A nullable cap is the loophole that makes the guarantee a
comment. The engine refuses to start without one; the plugin may raise it, not remove it.
⚠ **Defaults:** 25 min product / configurable in diagnostics — chosen against the 17-min beam-clearing
of 2026-08-14, so a genuinely slow fill is not cut off, and a bath-cleared one never comes close.

⭐ **L3 belongs to the host and nowhere else.** The engine only learns that time passed when someone
calls `offer(frame, t)`; a wedged camera stops calling it entirely, so **an engine-side timer cannot fire
on a dead stream.** The host's pump owns that watchdog — it is the only party that knows a frame did not
arrive.

⛔ **On any cap, the last row is NOT the answer** (§2.5). The outcome is `NEVER_SETTLED` / `STALLED`, and
the operator is told which.

### 12.3 The outcome set — closed, and every one of them is said out loud

| outcome | means | value? |
|---|---|---|
| `SETTLED_IMMEDIATE` | the fill arrived clear (§9.6) | ⭐ yes — the first settled window |
| `SETTLED_AFTER_CLEARING` | it cleared in the beam | ⭐ yes — the vertex read |
| `NEVER_SETTLED` | `maxSeconds`/`maxFrames` hit with the gate never firing | ⛔ **no** |
| `MEASUREMENT_BROKEN` | `A_Soret` under the §3.1 floor on the first full rows | ⛔ no — ⭐ and abort **at once**, do not burn 25 minutes of lamp on a broken fill |
| `CANCELLED` | the operator stopped it | ⛔ no (evaluator may override) |
| `STALLED` | frames stopped arriving | ⛔ no |

---

## ⭐⭐ 13 · WHAT THE OPERATOR SEES — and why a percentage would be a lie  *(Edwin, 2026-08-17)*

> *"for the simple-50-frames run we used the app's main status area and offered a progress bar. For the
> new algorithm things turn more complicated from a UX point of view."* ⭐ They do, and the reason is
> exact: **a monitored run has no known end time**, so the one thing the old UI showed — a fraction of a
> known total — does not exist.

### ⛔ 13.1 THE RULE

⛔ **Never show a percentage against an unknown end.** A bar creeping to 90 % and sitting there is worse
than no bar: it makes the operator distrust a wait that is working correctly.

### ⭐⭐ 13.2 WHERE IT GOES — Edwin's placement, and it is better than the first sketch  *(2026-08-17)*

> ⚠ The first draft drew a "sparkline in the capture panel" and Edwin could not tell what widget that
> was meant to be — fairly, because it was not any widget this app has. His proposal instead:
>
> *"the information should be displayed in a Spectral step view (and make the app's progress bar
> indefinite) … put the info about settlement into the spectral graph as a kind of legend box."*

⭐⭐ **Adopt it. It reuses three things that already exist instead of inventing a fourth:**

```
  ┌ app status bar ─────────────────────────────────────────────────────────────┐
  │  Measuring sample …          [ ///////// indeterminate /////// ]  [Cancel]  │  ⭐ no fake %
  └─────────────────────────────────────────────────────────────────────────────┘

  ┌ the ACQUISITION step's own view — where the operator is already looking ─────┐
  │                                                                             │
  │      the live spectrum plot, exactly as today                               │
  │                                             ┌─ legend box (plugin-authored)─┐│
  │                                             │ state      clearing …        ││
  │                                             │ elapsed    2:14  / max 25:00 ││
  │                                             │ turbidity  0.087  ↓ 0.011/min││
  │                                             │ Q% (prov.) 14.1              ││
  │                                             └──────────────────────────────┘│
  └─────────────────────────────────────────────────────────────────────────────┘
```

| the piece | what it reuses |
|---|---|
| indeterminate status bar | ⭐ `ApplicationStatusSignal` already carries `stepsCount` / `currentStepIndex` — ⚠ **`stepsCount = 0` becomes the indeterminate convention**, a one-line host change |
| the legend box | ⭐ **`LegendPosition` + `MetricFieldView` / `LabelView` already exist** — key/value lines the plugin authors and the host renders blind. ⛔ Nothing new to invent |
| the step view | ⭐ acquisition steps already carry a view (`step.getView()`, the `CaptureView` the capture window is read from) |

⭐ **The convergence trace is a SECOND element** — a small `SeriesPlotView` (generic x/y + a threshold
`addLevel`, the same vocabulary `SpectrumPlotView` already speaks, but x = minutes rather than nm).
⚠ It is the one genuinely new view type, so the legend box still ships first — the box alone makes the
wait legible. ⭐ **But it is no longer optional**: §18's settling step needs the same view model, so it is
built once and used three times (live, diagnosis tab, PDF).

⭐⭐ **The falling number IS the progress indicator** — `turbidity 0.087 ↓ 0.011/min` against a
threshold of 0.0017/min tells the operator both *where* it is and *how fast it is getting there*, which
a percentage never could.

### ⭐ 13.3 IT ALL COMES FROM THE PLUGIN — one view-model, host renders it blind

```
   evaluator.coach(rows) -> CoachMessage(
        state    = "clearing …"                         ⭐ the plugin's wording
        fields   = [("elapsed", "2:14 / max 25:00"),    ⭐ the LEGEND BOX lines, in the plugin's
                    ("turbidity", "0.087  v 0.011/min"),   own words and its own order
                    ("Q% (prov.)", "14.1")]
        series   = ("turbidity", values, target=0.0017) | None    ⭐ optional trace (§13.2)
        progress = DETERMINATE(0.57)                     ⭐ the plain burst: "frame 34 / 60"
                   | INDETERMINATE                       ⭐ a monitored run: no fraction exists
        severity = INFO | WARN | ⛔ BLOCKED )
```

⭐ The host renders a series it cannot interpret, under a label it did not choose. It never learns that
"turbidity" is `A_valley` over 500–560 nm — the §10.1a-bis boundary, held in the UI layer too.
⭐⭐ **And `DETERMINATE` is what makes §10.6 whole:** the burst evaluator returns a fraction, and today's
`"Capturing sample frame 34 / 60"` status line is reproduced **unchanged, through the new path**.

⚠ **Refresh rates** (rows arrive at ~1.4 Hz and jitter ±0.06):

| | |
|---|---|
| the state word | ⭐ immediately on change |
| numbers in the status line | ⚠ no faster than ~2 s — a value flickering at 1.4 Hz reads as instability, not information |
| the convergence trace | every row |

### 13.4 The endings, also plugin-authored

```
   ⭐ settled at 16:42 — measuring
   ✅ Q% 13.3   good — green            (17 min, 21 captures)
   ⛔ the fill never cleared in 25 min — no value. Warm it and try again.   (NEVER_SETTLED)
   ⛔ cancelled — nothing recorded.                                          (CANCELLED)
   ⛔ no signal in the Soret band — check the fill and the lamp.             (MEASUREMENT_BROKEN)
```

⚠ §2.5's guards keep their own wording; **an outcome without a value must always say why**, or the
operator learns to read a missing number as a bug.

---

## ⭐⭐ 14 · THE ALGORITHM, IN FULL  *(the normative statement — §2 is the summary)*

### ⭐⭐ 14.0 IN PLAIN WORDS FIRST — *"do you want a threshold of the `A_valley` change per time unit?"*  *(Edwin, 2026-08-17)*

⭐ **Yes — exactly that, and here is the whole idea in five lines.**

```
   1  Every ~35 s the ring has 50 FRESH frames -> one independent mean spectrum.
   2  From it, one number that tracks TURBIDITY:  A_valley  (absorbance, 500-560 nm).
   3  Compare it with the PREVIOUS independent one and divide by the minutes between them
      ->  a RATE:  "turbidity is still falling by 0.011 per minute".
   4  When that rate is small twice in a row, the sample has STOPPED CLEARING.
   5  Only then is Q% read — and which way it is read depends on whether there WAS a fall at all.
```

**Why a rate and not a difference:** a difference only means something if you also say *how long*
between the two numbers. §2.1's original "0.005" silently meant *per 3-minute sample*; write it as a
rate and the criterion stops depending on how often you happen to look (§14.3).

**What it looks like on the real curve** (2026-08-14, jar B — the run this is derived from):

| t | `A_valley` | rate since the previous independent window | verdict |
|---|---|---|---|
| 0 min | 0.9455 | — | turbid, and hugely so |
| 3 min | ~0.35 | ≈ −0.20 /min | ⛔ still clearing, nowhere near |
| 12 min | ~0.05 | ≈ −0.010 /min | ⛔ still above the threshold |
| **16.7 min** | **0.0257** | **≈ −0.0015 /min** | ⭐ **below 0.0017 twice running ⇒ SETTLED** |
| 90 min | 0.0089 | ≈ −0.0002 /min | (it keeps creeping, and it no longer matters) |

⭐ **`A_valley` fell 97 % across that run** — which is why it is the gate: the thing being watched moves
by a factor of 40, while `Q%` (the answer) moves by ~1.5 units against a 0.063 noise floor. ⇒ **gate on
the big signal, read the small one.**

### 14.1 The constants — every one of them the plugin's

| | | |
|---|---|---|
| `W` | 50 frames (~35 s) | the evaluation window |
| `R` | 60 frames | retention (§9.1a) |
| `minW` | 20 frames | the smallest window allowed to emit a **provisional** row |
| `θ_gate` | **0.0017 / min** | flatness of `A_valley` — ⭐ §14.3, this is §2.1's 0.005 re-expressed |
| ⭐ `j` | **2 windows** | ⭐ the comparison spans `k` vs `k−2` (~70 s) — §14.2b's noise budget, **not** adjacent |
| `k_gate` | 2 | consecutive decision comparisons (⭐ TEST A, §14.5) |
| ⭐ `m_trend` | **5 decision rows** | the re-clouding trend baseline (⭐ TEST B, §14.5) |
| ⭐ `m_degrade` | **10 decision rows** | the degrading-fill trend baseline (⭐ TEST C, **§31**) — ⚠ DESIGN, not built |
| ⭐ `k_sig` | **4 × stdErr** | TEST C's significance term — ⭐ **no magnitude term at all**, which is the whole point (§31.3) |
| ⭐ `W_gate` | **= `W`** | ⛔ NOT an open value — §14.2b's algebra refutes a shorter gate window |
| `mat` | 0.010 | how far `A_valley` must have fallen to call the fill "was clearing" |
| `σ_Q` | 0.063 | the no-re-seat floor, used only for the rise sanity check |
| caps | 25 min / ~2000 frames | ⭐ the **engine's**, not the evaluator's (§12.2) |

### ⭐⭐ 14.2 THE STATES

```
  FILLING       ring < minW                 no rows at all
  PROVISIONAL   minW <= ring < W            ⚠ rows emitted for DISPLAY ONLY — never gated on, never fitted
  WATCHING      ring == W                   full rows; every W-th one is a ⭐ DECISION ROW
                                            ⛔ MEASUREMENT_BROKEN if A_Soret < 0.15 on the first full rows
       │        ⭐ TEST A (flatness, |rate(k,k-2)| < θ, x k_gate)  — may FIRE the gate
       │        ⭐ TEST B (re-clouding trend over m rows)          — may RESET it   (§14.5)
       │        ⭐ TEST C (degrading trend, slope > 4*stdErr, NO θ)   — may END it    (§31)
       │
       ├─ gate fires ── A_valley fell >= mat below its MAXIMUM ──▶ CLEARING branch
       │                otherwise ─────────────────────────────▶ ARRIVED_CLEAR branch
       │
  ARRIVED_CLEAR   answer = the gate row itself           -> promote, STOP  (SETTLED_IMMEDIATE)
  CLEARING        answer = parabola vertex around the Q% MINIMUM (its three neighbours)
                                                         -> promote, STOP  (SETTLED_AFTER_CLEARING)
       ⛔⛔ CORRECTED 2026-08-17: this said "the vertex through rows (g-1, g, g+1)" — AROUND THE GATE ROW.
          On the real curve the minimum is at t = 16.66 while the gate confirms at t = 19.93, so those
          are DIFFERENT rows, and fitting around the gate row fits a RISING RAMP whose parabola has no
          minimum at all (the a<=0 guard then silently returns a raw, later, browner value).
          ⭐ The read is around the MINIMUM; the gate only says WHEN IT IS SAFE TO LOOK.
          ⭐ And the promoted SPECTRUM is the minimum row's, not the gate row's — §14.6's latch stores
             which row won, so the answer's spectrum is a real capture from the right moment.
  cap reached before the gate fires                      -> STOP, ⛔ NO VALUE (NEVER_SETTLED)
```

### ⭐⭐ 14.2a THE STARTUP COST — "must 50 frames be captured before there is any metric?"  *(Edwin, 2026-08-17)*

⭐ **Yes — and worse: the gate needs THREE full windows, not one.** §14.2 already has the states, but the
wall-clock consequence was never priced, and §9.6a's "~35 s" was wrong because of it.

```
   frame     0 ────────── 20 ────────── 50 ────────── 100 ───────── 150
             │ FILLING     │ PROVISIONAL │ decision #1 │ decision #2 │ decision #3
             │ no rows     │ display only│             │ ⭐ 1st rate  │ ⭐ 2nd rate -> GATE MAY FIRE
   at 1.0-1.5 fps:                        33-50 s       67-100 s      100-150 s
```

| | why it is unavoidable |
|---|---|
| the 1st window | ⛔ a rate needs **two** numbers; one window can be compared with nothing |
| the 2nd | gives the first rate |
| the 3rd | `k_gate = 2` — ⭐ two *consecutive* flat comparisons, so one lucky quiet interval cannot settle a turbid fill |

⇒ ⭐ **earliest possible answer ≈ 1.7–2.5 min after insertion** (plus the reference burst and the jar
swap before it). ⚠ Damage banked by then is **0.03–0.07 `Q%`** — still at or under the 0.063 floor, so
§9.6a's conclusion survives; only its arithmetic was optimistic.

⚠ **REVISED AGAIN BY §14.2b:** the adopted comparison is `j = 2` windows apart, not adjacent, so the
count is **4 windows ≈ 2.2–3.3 min**. The reasoning above is unchanged; only `j` moved.

#### ⭐⭐ 14.2b THE NOISE BUDGET — ⭐ D1/D2 RESOLVED, and the "short gate window" idea is REFUTED  *(2026-08-17)*

> §17/D2 said the gate's *resolvability* was unverified and §14.2b proposed a short gate aperture to
> settle sooner. ⭐ **Both are now settled — analytically, from a number the archive already contains.**

**The one number that unlocks it.** The no-re-seat `Q%` floor is **sd 0.063** (§16.36.6), and
`Q% = 100·(A_Q − A_valley)/A_Soret`. With `A_Soret ≈ 0.61`:

```
   0.063 = 100 * sigma(A_Q - A_valley) / 0.61     ->  sigma(diff)  ~ 0.00039
   the two band means, independent and comparable ->  sigma_A(60 frames) ~ 0.00027
   per FRAME                                      ->  sigma_1 = 0.00027 * sqrt(60) ~ 0.0023
```

⚠ An **upper bound**: the 0.063 floor also contains lamp and holder terms that are not band-mean noise.
⇒ conservative, which is the right direction. ⭐ Confirm it directly on the `.npz` corpus (§11.8a).

**The budget.** Comparing window `k` with window `k−j` (centres `jW/fps` apart):

```
   sigma_rate  =  sqrt(2) * sigma_1 * fps * 60 / ( j * W^1.5 )     [ per minute ]
```

| `W` | `j` | σ_rate (/min) | θ = 0.0017 is… | verdict |
|---|---|---|---|---|
| 50 | 1 (adjacent) | 0.00078 | **2.2 σ** | ⚠ workable but thin — §17/D2's worry was real |
| ⭐ **50** | ⭐ **2** | **0.00039** | ⭐ **4.4 σ** | ⭐ **ADOPTED** |
| 30 | 2 | 0.00084 | 2.0 σ | ⚠ marginal |
| 20 | 2 | 0.00154 | 1.1 σ | ⛔ unusable |

⚠ **Measured correction, §23/V1 (2026-08-17):** ~18 % of captured frames are duplicates of their
predecessor, so `W = 50` carries **41 independent frames** and every σ above is **× 1.10**. ⇒ the adopted
row becomes ⭐ **4.0 σ** — unchanged in kind, and the short-window rows get worse, not better.

#### ⛔⛔ AND THE ALGEBRA REFUTES THE SHORT-GATE IDEA OUTRIGHT

At a **fixed wall-clock cost** `C = (j+1)·W` frames, substituting `W = C/(j+1)`:

```
   sigma_rate  ∝  (j+1)^1.5 / ( j * C^1.5 )        ->  j = 1: 2.83   ⭐ j = 2: 2.60
                                                       j = 3: 2.67      j = 4: 2.80
   and at fixed j:  sigma_rate ∝ W^-1.5            ->  ⭐ BIGGER windows, always
```

⇒ ⭐⭐ **For a given number of seconds, the fewest and largest windows win.** Splitting the same frames
into more, smaller windows *raises* the rate noise — so "gate on a short window to settle sooner" is a
**false economy**, and §14.2b's first draft was wrong. ⛔ `W_gate` is not an open value: **`W_gate = W`**.
⭐ `j = 2` is the shallow optimum, and that is why it is the default rather than an arbitrary choice.

⇒ **REVISED TIMING** (supersedes §14.2a's figure): comparisons are (win 3 vs 1) and (win 4 vs 2), so the
gate can first fire after **4 windows = 200 frames ≈ 2.2–3.3 min**. ⚠ Damage banked: **0.04–0.09 `Q%`**,
still at or about the 0.063 floor — §9.6a's conclusion stands, at 4.4 σ of margin instead of 2.2.

### ⭐⭐ 14.3 THE TRAP THIS DESIGN NEARLY WALKED INTO — decisions run on NON-OVERLAPPING windows

⛔⛔ **§2.1's threshold cannot be applied to adjacent rolling rows, and applying it would break the gate
silently.** Consecutive rows are **one frame apart and share 49 of 50 frames**, so `ΔA_valley` between
them is ~50× smaller than between the 3-minute samples the 0.005 was derived on. ⇒ the gate would fire
on the **first two rows of every run**, always, and the instrument would confidently report turbid fills.

⭐ **Three rules together fix it** — the third added by §17/D2, because two were not enough:

```
   1  DECISIONS use only every W-th row      ->  the windows compared never overlap
   2  the threshold is a RATE                ->  |dA_valley/dt| < 0.0017 per minute
   3  ⭐ the COMPARISON SPANS >= 70 SECONDS   ->  walk back to the first decision row that far away
```

⛔⛔ **RULE 3 CORRECTED DURING IMPLEMENTATION (2026-08-17), and the correction is the point of it.** It
first read *"the comparison spans j = 2 windows"*. ⚠ That is only the same statement while a window is
~35 s long. Replayed on the real 2026-08-14 curve — whose samples are **3.28 minutes apart** — "j = 2"
doubles a span that was already ample, and the gate fires **two samples late**. ⇒ ⭐ **the span is
expressed in SECONDS and the evaluator walks back to reach it**, which makes the criterion identical on
live 35-second windows and on a replayed CSV. `j = 2` remains what that rule *yields* at the shipped
window size; it was never the thing being specified.

⛔⛔ **WHY RULE 3 IS NOT OPTIONAL — the conversion preserved the threshold's VALUE but not its
RESOLVABILITY.** The original 0.005 compared block means **3 minutes** apart; adjacent 50-frame windows
are **35 s** apart, so the same rate is a ~5× smaller absolute difference against per-window noise that
is *no smaller at all*. §14.2b prices it: adjacent gives θ = **2.2 σ**, `j = 2` gives **4.4 σ**.
⚠ ⛔ **Rule 2 alone was therefore a half-fix** — it made the criterion aperture-independent *in
expectation* while leaving it noise-limited in practice. That is precisely the kind of error that would
have shown up as "the gate fires early on some fills and late on others", i.e. as unexplained scatter.

⚠ Rule 2 still buys what it was for: the gate is **independent of `W` and of the frame rate**, so a
faster camera does not silently re-tune the criterion — ⭐ but `j` must then be chosen against §14.2b's
budget, not inherited.
⭐ **R1's acceptance test:** replayed on 2026-08-14, the rate form with `j = 2` must fire on the **same
sample** the 3-minute form did (t ≈ 16.7). If it does not, the conversion is wrong and nothing else in
this section may be trusted.
⚠ Display keeps every row; only decisions are decimated.

### 14.4 The loop, as code

```python
def offer(frame, t):                                   # MonitorEngine — mechanics only
    ring.add(frame, t)
    if len(ring) < policy.minWindow:      return None
    if not cadence.due():                 return None
    window   = ring.window(policy.windowFrames)        # <= W frames
    spectrum = MeanOp(window)                          # ⭐ C1 rejection inside — §9.5
    row      = evaluator.evaluate(spectrum)            # the PLUGIN's metrics
    row.t    = (window.firstT + window.lastT) / 2      # ⭐ centre stamp — §9.3
    row.provisional = len(window) < policy.windowFrames
    rows.append(row)
    if row.isDecisionRow:                              # every W-th full row
        decision = evaluator.decide(rows)              # the PLUGIN's gate + read + stop
        #   inside decide():  TEST A  |rate(k, k-2)| < theta,  k_gate consecutive   -> settle
        #                     TEST B  signed trend over m rows > 0                  -> reset (§14.5)
        if decision.promotes:  best = (row, spectrum)  # ⭐ promoted OUT of the ring — §9.1a
        if decision.stops:     finish(decision.outcome)
    if elapsed > policy.maxSeconds or n > policy.maxFrames:
        finish(NEVER_SETTLED)                          # ⭐ L2, and the evaluator cannot veto it
    return row
```

⚠ **§2's step 6 is superseded here.** It said *stop once a rise > 3σ confirms the minimum*; that costs
**~10 further minutes of light** (§2.1 measured it) for a moment the `A_valley` gate already found. ⇒ the
stop is **one decision row after the gate**, and the rise test is kept only as a **sanity check written
into the record** — if `Q%` does not subsequently rise, the run says so rather than silently disagreeing
with the model.

### ⛔⛔ 14.5 THE RE-CLOUDING DIP — Edwin's catch, and it BREAKS the gate as written above  *(2026-08-17)*

> *"i could imagine that the sample muddies a little bit again when it is put into the spectroscope, as
> the spectroscope might be cooler than the warm bath."*

⭐⭐ **This is not a maybe — §16.36.7 makes it near-certain.** The cloud point is between **35 and 50 °C**,
the bath is at **52 °C**, and the holder in the beam sits at **~40 °C** *once the lamp has been running*.
A jar leaving the bath therefore **cools toward, and can cross, its own cloud point** — and if the
instrument is cold (lamp just switched on, cool room), it crosses it for certain.

```
   A_valley                    ⭐ THE SHAPE THE FIRST DRAFT DID NOT ALLOW FOR
      │        ___
      │      _/   \__                re-clouds as the jar cools
      │    _/        \__
      │   /             \____        then the lamp re-warms it and it clears again
      │  •                   \_____________________
      └──────────────────────────────────────────────▶ t
        insertion
```

⛔ **Three ways this defeats the gate exactly as §14.2 states it:**

| ⛔ | why |
|---|---|
| the gate fires **at the top of the dip** | at a turning point the rate passes through zero — "flat" is momentarily true while the sample is at its **worst** |
| a slow re-cloud reads as flat | a rise of +0.001/min is under the 0.0017 threshold in **magnitude**, and `\|ΔA\|` cannot tell up from down |
| the branch test misfires | "did it fall materially?" compared against the **first** row is wrong when the first row was the clearest one of the run |

⭐⭐ **THE FIX — ⭐ REVISED PER §17/D1, 2026-08-17. TWO TESTS, NOT ONE OVERLOADED COMPARISON.**

⛔⛔ **The first draft said "settle requires `−θ ≤ rate ≤ 0`" and that is WRONG** — on an already-clear
fill the true rate is **zero**, so the measured rate is **zero-mean noise**: requiring `≤ 0` rejects half
of all comparisons at random, and `k_gate = 2` turns that into ~25 % success per attempt. ⛔ The fast
path would have become a lottery. ⭐ The intent (reject a *systematic* rise) was right; one comparison
cannot carry both jobs, because **flatness is a question about magnitude and re-clouding is a question
about direction**, and they need different baselines.

```
   ⭐ TEST A — FLATNESS   (short baseline, MAGNITUDE, per §14.3)
        |rate(k, k-2)| < 0.0017 /min,  for k_gate = 2 consecutive decision rows
        ⭐ symmetric, exactly as originally derived; noise is 4.4 sigma below it (§14.2b)

   ⭐ TEST B — RE-CLOUDING   (long baseline, SIGNED, sustained)
        least-squares slope of A_valley over the last m = 5 decision rows
        significantly > 0  (slope > 2 * its own standard error, and > 0.0017 /min)
        ->  RE-CLOUDING: reset the k_gate counter, restart clearingSeconds (§2.4),
            and ⭐ tell the operator (§13) — it is a diagnosable condition, not a glitch

   3  the fall test ("did it clear?") uses the MAXIMUM A_valley seen, never the first row
```

⭐⭐ **Why B needs the longer baseline and A does not.** A single 70-second comparison cannot separate a
+0.001/min drift from noise — that is exactly the 50/50 coin the first draft flipped. Over **five**
decision rows (~6 min) the trend's standard error falls by roughly `√m` **and** the lever arm grows, so a
real re-cloud becomes unambiguous while noise does not. ⇒ ⭐ **A decides "has it stopped?", B decides "is
it going the wrong way?", and neither is asked the other's question.**

⚠ **And the gate must not fire before the peak has been passed.** Refuse to settle until at least one
decision row has shown a **fall** since the maximum. A fill that is flat from the start satisfies this
trivially (max = first row, no fall required), so the arrived-clear branch is unaffected.
⚠ Test B costs nothing before its 5 rows exist; until then only A runs, which is correct — a re-cloud
cannot be *established* from fewer points than that anyway.

> ⭐⭐ **AND THERE IS A THIRD CASE THAT NEITHER TEST CAN SEE — §31, added 2026-08-19.** A fill that is not
> re-clouding but *ripening* rises **monotonically at a rate far below θ** (0.0012 /min measured), so TEST A
> calls it flat and TEST B stays silent — while `__hasFallenSinceMaximum` blocks the gate on every row and
> stalls the run **without a word**. ⛔ **Do not fix this by lowering θ:** TEST B moves `huntFrom` (§30.8),
> which on a ripening fill discards the only good look in the run. ⇒ **TEST C is the mirror image of TEST B,
> not another instance of it** — see §31.3's table.

### ⭐⭐ 14.6 THE LATCH — the answer is fixed when it is read, and observation cannot change it  *(2026-08-17)*

⭐ **The diagnostic run continues past the read** (§11.8); the product stops. That is **one flag**, and it
is the only algorithmic difference between them (Edwin's framing, and it is right) — ⛔ **but only if the
answer is LATCHED.**

```
   read fires  ->  answer := (value, t, spectrum)   ⭐ FROZEN. Later rows are appended to the
                                                        trajectory and can NEVER become the answer.
```

⛔ **Without the latch, "keep observing" silently corrupts the measurement.** On the clearing branch the
read is a **minimum**; twenty further minutes of noisy rows around a rising ramp will eventually produce
one row that dips below it, and a naive "best so far" would hand back a **noise excursion 15 minutes
into the photodamage** instead of the settled value. ⚠ That is the same selection bias §2.2 rejected the
raw minimum for — reintroduced through the back door by a longer run.

⇒ ⭐ **`answer` is latched; `promote` stops after the read.** The tail is data, not a candidate.

### ⭐⭐ 14.5a AND THE PROTOCOL RULE THAT FOLLOWS — pre-warm the instrument

⭐ **The lamp must be on and the holder at working temperature BEFORE the jar goes in.** Otherwise every
bath-cleared fill re-clouds on arrival and the ~30-second recipe silently becomes a 10-minute one — with
the extra light dose that implies.
⚠ **This lands on §11 directly:** if the four arms are run in sequence over an evening, the holder is
cold for arm (a) and warm for arm (d), which would put a temperature confound exactly where the
experiment is trying to measure a temperature effect. ⇒ **pre-warm once, keep the lamp on between arms,
and log the holder state per arm.**

⭐ **The dip is also worth surfacing to the operator** — it is a real, diagnosable condition
("the jar cooled below its cloud point on the way in"), not a glitch, and the coach line can say so.

---

## ⭐ 15 · WHAT IS STORED — and how the winning run is retrievable  *(Edwin, 2026-08-17)*

### ⭐⭐ 15.1 THE ANSWER'S SPECTRUM GOES WHERE A SPECTRUM ALWAYS WENT

```
   step.container[SAMPLE]  <-  the winning window's MEAN SPECTRUM
```

⭐⭐ **That single line is the entire integration.** PROCESSING, EVALUATION, the gauge, the PDF and the
LIMS publish are **completely unchanged** — they receive one sample spectrum, exactly as they always
have. The monitor changes *which* spectrum that is, not what happens to it.

### ⭐⭐ 15.2 Beside it, a `MonitorRecord` — GENERIC key/value, on the SpectralWorkflow  *(Edwin, 2026-08-17)*

> *"the settlement history should be stored in the SpectralWorkflow (but not the whole bunch of
> spectra) … the MonitorRecord should be set up in a generic way holding key-value pairs, as one plugin
> might have other records than another."*

⭐⭐ **Agreed, and it is the same boundary as everywhere else in this design: the host stores what it
cannot interpret.** ⛔ A record with fixed columns `qPercent / soret / valley / qBand` would hard-code
one plugin's physics into the app's persistence layer — the exact mistake §10.1a-bis just removed from
the SDK.

```
   MonitorRecord                              ⭐ on the SpectralWorkflow, NOT on the spectra
     evaluatorId, evaluatorVersion            who produced this, and under which rules
     policy        {W, R, cadence, caps}      ⚠ so runs made under different rules are never
                                                 silently compared
     outcome, cancelled, capsHit              §12.3 — a stopped run must never read as a finished one

     columns  [ {key, label, unit} ... ]      ⭐ SELF-DESCRIBING: the plugin names its own columns.
                                                 The host renders label+unit and interprets nothing.
     rows     [ {t: 1013.4, <key>: <value>, ...} ... ]     ⭐ plain key/value dicts

     answer   { valueKey, value, t, rowIndex, readAs, branch }
                                              ⭐ the plugin says WHICH column is the answer, so
                                                 tooling finds it without knowing what Q% is
```

⚠ **One concession to genericity, and it is deliberate:** `t` is the single key the host is allowed to
know, because it draws the x-axis with it, and `answer.valueKey` must name a column that exists. ⭐ That
is enough for the history tracker and the PDF to find the number **without any plugin-specific
knowledge** — self-describing rather than schema-free.

| still recorded, as ordinary keys | why it matters |
|---|---|
| `clearingSeconds` | ⭐ §2.4 — a σ_fill component, not a curiosity |
| `branch` (arrived-clear / was-clearing), `readAs` (FIRST_SETTLED / VERTEX) | ⭐ changes what the value *means*; §16.34.3d makes this load-bearing |
| `nAccepted` per row | a run where C1 quietly ate half the frames must be visible afterwards |
| ⭐ the re-clouding dip, if it happened (§14.5) | it explains an otherwise inexplicable clearing time |

⭐ **Decision rows only** (~35 for a 20-min run, a few KB of JSON): the ~1700-row display trace is UI
detail, and storing it would put ~80 KB of noise into every measurement.
Home: the workflow's own record, persisted in the `DbMeasurement` JSON blob of
`SPEC_workflow_persistence.md` — ⚠ **mind that spec's float-key gotcha** when the rows are serialised.

### ⛔ 15.3 WHAT IS **NOT** STORED IN THE PRODUCT

| | |
|---|---|
| ⛔ raw frames (~1 MB per window, ~34 MB per run) | not in the app DB, not in the PDF |
| ⛔ every rolling row | see above |
| ⭐ diagnostics instead | the `.npz` of the whole raw run, on disk beside the CSV — which is what makes replay (§10.1) and post-hoc re-windowing (§9.3) possible |

⇒ ⭐ **The product stores enough to re-examine the DECISION; diagnostics store enough to re-run the
ALGORITHM.** Those are different questions and they deserve different budgets.

⚠ **The PDF (M2) shows the trajectory plot and the outcome line**, not just the number — a value whose
justification is a curve should not be published without it.

---

## 16 · Related

| topic | where |
|---|---|
| the two processes, and the controls behind them | `SPEC_capture_quality.md` §16.36 |
| what it re-weights — "the same oil" was not the same oil | §16.36.8 |
| the σ_fill design change it forces | §16.34.3d |
| `Q%`, the guards, the frozen windows | `SPEC_v_metric_integration.md`, `SPEC_metric_research.md` §10 |
| the working prototype | `diagnostics/clearing_time_course.py` |
| the shutter this would unblock, and the cloud point that forces it | `SPEC_capture_quality.md` §16.36.7 |
| the optical path a heater must not disturb | `SPEC_lamp_rebuild.md` §12.5 |
| the shape distance `D` the experiment reads out | `SPEC_history_tracker.md` |
| the Qt-free tier the monitor must live in | `SPEC_project_structure.md` |
| the `frameProvider` seam the host adapter reuses | `SPEC_plugin_driven_convergence.md` §9.1 |
| the water bath, measured | `SPEC_capture_quality.md` §16.36.7, §16.36.9 |

---

## ⭐⭐ 17 · RUBBER-DUCK PASS — the CONCEPT and the UX, walked end to end  *(Edwin asked for it, 2026-08-17)*

> ⚠ Deliberately **not** a code review. This walks the operator's session and then the concept's own
> internal consistency, in the style of `SPEC_capture_quality.md` §17.6/§17.7. ⛔ Findings that change
> the design are marked **D**, UX changes **U**, and the one strategic gap **C**. Several of these
> contradict things written earlier in THIS spec; that is the point of the exercise.

### ⭐ D1 — ✅ **RESOLVED IN §14.5** *(2026-08-17)* — §14.5's SIGNED RULE MISFIRED ON EXACTLY THE CASE THE PRODUCT CARES MOST ABOUT

> ⭐ **Fixed at the source:** §14.5 now specifies **TEST A** (flatness, magnitude, short baseline) and
> **TEST B** (re-clouding, signed trend over `m = 5` decision rows) as two separate tests. The finding
> below is kept as the reasoning that forced it.

§14.5 hardened the gate against re-clouding: *"settle requires `−θ ≤ rate ≤ 0` — a rising `A_valley` is
never flat."* ⛔ **Walk that against an already-clear fill and it breaks.**

```
   a bath-cleared fill:  TRUE rate = 0  ->  the MEASURED rate is zero-mean NOISE
   requiring rate <= 0   ->  ~50 % of comparisons rejected AT RANDOM
   requiring 2 consecutive  ->  ~25 % success per attempt  ->  ⛔ ~4 attempts on average,
                                                                and the wait becomes a lottery
```

⭐ **The intent was to reject a SYSTEMATIC rise, not noise — and one comparison cannot carry both jobs.**
⇒ **split the two tests:**

| test | window | form |
|---|---|---|
| ⭐ **flatness** | short (adjacent decision windows) | `\|rate\| < θ` — ⭐ **magnitude**, as originally derived |
| ⭐ **re-clouding** | long (a trend over m decision rows, where noise averages down) | ⭐ **signed and sustained**: only a trend significantly > 0 resets the gate |

⛔ **Do not** implement §14.5's rule as written. §14.5's *intent* stands; its formulation is replaced here.

### ⭐ D2 — ✅ **RESOLVED IN §14.2b / §14.3** *(2026-08-17)* — THE GATE'S RESOLVABILITY WAS UNVERIFIED, AND THE RATE FORM DID NOT FIX IT

> ⭐ **Fixed at the source, and it went further than the finding asked:** §14.2b derives the noise budget
> from the measured 0.063 floor, adopts **`j = 2`** (θ = 4.4 σ instead of 2.2 σ), and ⛔ **refutes the
> short-gate-window idea outright** — at fixed wall-clock, fewer and larger windows always win, so
> `W_gate = W`. §14.3 carries it as rule 3. ⚠ One check remains: confirm `σ_1` directly on the `.npz`
> corpus rather than inferring it from the `Q%` floor. The finding below is the reasoning.

§14.3 converted `0.005 per 3-minute sample` → `0.0017 /min` and called it aperture-independent. ⭐ True
**in expectation** — ⛔ **false for its noise.** The original threshold compared block means **3 minutes
apart**; adjacent 50-frame windows are **35 s apart**, so the same rate corresponds to an absolute
difference ~5× smaller, against per-window noise that is **no smaller at all**.

```
   the threshold's VALUE survives the conversion.   ⭐
   the threshold's RESOLVABILITY does not.          ⛔ and nothing measured it.
```

⚠ **This is the same open measurement as §14.2b, but it bites at the DEFAULT aperture, not only at the
short one** — the gate as specified may be noise-limited even at `W = 50`.

⭐ **The fallback, if the `.npz` re-windowing says it is:** keep the **comparison interval** near the
~3 minutes the threshold was derived on (compare window *k* with window *k−5*), independent of `W`. The
gate is then exactly as noise-limited as the version that provably worked, and the ring buffer keeps its
phase resolution. ⚠ Cost: the earliest settle moves out to ~6 min.
⇒ ⛔ **`θ`, `W_gate` and the comparison interval are ONE decision, and it is a measurement, not a choice.**

### ⚠ D3 — WHO CHOOSES DIAGNOSTIC MODE? Not the plugin

§11.9c made "run past the read" a policy flag but never said who sets it. ⛔ If the **plugin** does, the
DEV plugin is diagnostic everywhere — including in an end-user's wizard. ⇒ ⭐ **the mode is a HOST
argument to `createMonitor(...)`**: the bench (master role) may offer it; the wizard hard-codes product
mode. ⚠ And it lands in the record either way (§11.9c).

### ⚠ D4 — THE REFERENCE AGES WHILE THE SAMPLE SETTLES

The reference is captured once, then a beam-clearing run can take **17–25 minutes**. §16.7 bounds the
blank's drift over exactly that span — it is not zero.
⛔ **Do not re-reference:** that means pulling the sample jar, and a re-seat costs **0.70 vs 0.063**
(§16.36.6) — eleven times the noise the re-reference would remove, plus the sample would have to settle
again. ⇒ ⭐ **record the reference's age with the answer** and flag runs whose duration exceeds the span
§16.7's bound was measured over. Honest beats clever here.

### ⚠ D5 — THE FILL-QUALITY GUARD MUST BE READ AT THE ANSWER, NOT AT THE START

The DN guard ("too concentrated / too dilute", `__logLowDnGuard`) is evaluated per capture today. ⛔ Under
a monitored run **DN moves with the turbidity** — that is what §16.33 measured. A guard evaluated on the
first window judges a fill that no longer exists. ⇒ ⭐ evaluate it on the **latched answer row**, and log
the first-window value only as a diagnostic.

### ⛔⛔ U1 — DO NOT SHOW A PROVISIONAL `Q%`. AT ALL.

§13.2's mock-up has `Q% (prov.) 14.1` in the legend box. ⛔ **Take it out.** A number displayed while
still moving is a number somebody will write down — and the settled value may differ by more than the
gauge's own decision boundaries. ⭐ Show the **state** and the **gate quantity** during the wait; reveal
`Q%` when it is latched, and never before. ⚠ The temptation to show it is strong, which is why this is a
rule rather than a preference.

### ⛔ U2 — A RE-RUN AFTER CANCEL IS NOT A FRESH RUN, AND THE UI CURRENTLY IMPLIES IT IS

§12.1 leaves the step "not captured" and re-enables Measure. ⛔ But the fill in the beam has **already
banked light dose**. Pressing Measure again does not repeat the experiment; it measures a browner
sample. ⇒ ⭐ after `CANCELLED`, `NEVER_SETTLED` or `MEASUREMENT_BROKEN`, the coach line must say so:

```
   ⛔ stopped after 6:20. This fill has been in the beam and has changed —
      a fresh fill gives a truer reading than re-measuring this one.
```

⭐ Same physics as §16.36; it has simply never been surfaced to a user before.

### ⭐ U3 — PREDICT THE FINISH, OR THE CAP IS A 25-MINUTE SILENCE ENDING IN NOTHING

Waiting to `maxSeconds` and then reporting **no value** is the most expensive failure in the design. ⭐
The curve itself says early on whether it will make it: extrapolate the current fall rate to `θ` and
offer a decision point.

```
   at 5:00   "still falling fast — about 14 more minutes at this rate.
              ⭐ Warming the jar would finish this in two."   [ Keep waiting ]  [ Stop ]
```

⚠ Present it as an **estimate that will move**, never as a countdown.

### ⚠ U4 — TWENTY MINUTES IS A LONG TIME TO HOLD A PANEL HOSTAGE

The capture runs inside a nested event loop with navigation disabled (§12.1). At 40 s that is invisible;
at 20 min it is an application that appears stuck. ⇒ ⭐ say so explicitly ("this can run unattended — it
will finish on its own"), consider a completion sound, and ⚠ on **Android the screen must be kept awake**
or the run dies with the display.

### ⚠ U5 — "FRAMES" NO LONGER MEANS WHAT THE COMBO BOX SAYS

The bench's Frames combo (50 / 60 / 150) means *total frames in the burst*. Under a monitor it becomes
the **window**, and a master picking 150 silently buys a 105-second aperture and a much later gate. ⇒ ⭐
relabel it (`Window (frames)`) in monitored mode, or hide it and show the window the plugin chose.

### ⚠ U6 — THE LEGEND BOX WILL COLLIDE AT PHONE WIDTH

Four key/value lines overlaid on a plot at **412 dp** (`SPEC_phone_width_responsiveness.md`) will cover
the trace it is annotating. ⇒ ⭐ overlay on the desktop, **reflow to a row beneath the plot** on phone
width. Decide it now; it is free at design time and irritating later.

### ⭐ U7 — THE RESULT SHOULD CARRY ITS OWN PROVENANCE

A value justified by a curve should not appear as a bare number. ⇒ ⭐ the result view shows
`settled after 2:14 · read as first-settled-window · 3 windows` — one line, and it makes §16.34.3d's
"the choice is load-bearing" visible instead of buried in a record.
⚠ §13.4's ending line says "21 captures" — ⛔ ambiguous now (frames? windows?). Say **windows**.

### ⛔⛔ C1 — THE STRATEGIC GAP: THE "TWO-MINUTE MEASUREMENT" ASSUMES A WATER BATH

⭐⭐ **This is the finding with the longest reach.** Everything in §9.6 that makes the product fast — the
arrived-clear branch, the ~2-minute answer, the near-zero pre-clearing damage — assumes the fill was
**cleared in a bath before insertion**. Without one:

```
   with a bath      arrives clear     ->  ~2 min      ⭐ the number this spec keeps quoting
   without a bath   clears in-beam    ->  ~17-20 min  ⛔ and the whole §16.36 damage budget comes back
```

⚠ **So the product's wait is bimodal, and which mode a customer lives in is decided by their bench, not
by our software.** ⇒ three consequences, none of them code:

| | |
|---|---|
| ⛔ marketing / the miller's expectation | the honest claim is **"about two minutes, if the sample is pre-warmed"** — never "two minutes" |
| ⭐ §7's heated holder | is re-weighted from *deferred nicety* to **the thing that makes the fast path real in the field** — it does the bath's job inside the instrument |
| ⭐ §11 | gains a second purpose: it is also the go/no-go on whether that fast path is chemically allowed at all |

⇒ ⭐⭐ **§11 is now load-bearing twice over**, and that is an argument for running it early — which is
exactly what §11.9 decided for independent reasons.

### 17.1 What this pass did NOT find

⭐ Worth recording, so the absence is evidence rather than an oversight: the **composition seam (§10)
survived the walk unchanged** — every finding above lands in an evaluator, a host argument or a view,
and **none** of them required the SDK to learn a wavelength or the plugin to own a loop. ⭐ That is the
strongest evidence so far that §10.1a-bis put the boundary in the right place.

---

## ⭐⭐ 18 · THE SETTLING STEP — a step-tab that holds the run's own history  *(Edwin, 2026-08-17)*

> *"we should also have another SpectralStep that holds graphs of the settlement history. This step is
> not selected during the measurement but it can be viewed for diagnosis, and should also enter the PDF.
> What should the graphs show? Q% should be depicted. Do we need our own plugin view model?"*

⭐ **Yes, and it costs less than it looks — because the view model it needs is the one §13.2 already
wanted for the live display.**

### ⭐⭐ 18.1 ONE VIEW MODEL, FED TWO WAYS — this is the whole economy of the idea

```
   DURING the run   ->  fed incrementally, rows arriving   ->  the live element (§13.2)
   AFTER  the run   ->  fed complete, from the record      ->  ⭐ the Settling step-tab (this section)
                                                               ->  and the same object renders into the PDF
```

⇒ ⛔ **not three features.** `SeriesPlotView` is built once; the live view, the diagnosis tab and the
report page are three *uses* of it. ⭐ That also settles §13.2's phasing question: the "optional second
element" is no longer optional, because the history tab needs it anyway.

### 18.2 What the graphs should show — two panels, and they must NOT share an axis

⚠ `Q%` sits near **13** and `A_valley` runs **0.9455 → 0.0257**. On one axis the gate quantity is a flat
line on the floor. ⇒ **two stacked panels, common x (minutes since insertion).**

```
  ┌ Q%  — the ANSWER's own history ──────────────────────────────────────────────┐
  │  22 ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  domain ceiling (§3.1a)               │
  │        •──•──●──•──•──•──•──•──•──•──•   ● = ⭐ THE LATCHED ANSWER            │
  │  12 ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  domain floor                         │
  ├ A_valley — WHY it was read there ────────────────────────────────────────────┤
  │   •                                                                          │
  │     •_                    ┊ gate fired                                       │
  │       •--•__•__•__•__•__•_┊_•__•__•__•     ┄┄ theta = 0.0017/min (§14.3)      │
  └──────────────────────────────────────────────────────────────────────────────┘
         0        2        4        6        8       10   minutes
```

| the panel must carry | why it earns its ink |
|---|---|
| ⭐ `Q%` per decision row | ⭐ Edwin's requirement, and the value's own provenance |
| ⭐ the **latched answer**, marked as a point | ⛔ without it the reader cannot see *which* row became the number |
| ⭐ `A_valley` + the θ level + the **gate-fire marker** | ⭐ the whole justification of *when* it was read — §14.5's re-clouding dip also becomes visible here, and only here |
| the §3.1a domain band on `Q%` | says at a glance whether a verdict was allowed — ⛔ **as a header chip, NOT as axis levels**: §18.7 shows drawing 12–22 crushes a 0.5-unit trajectory into a flat line |
| ⚠ a health strip — `A_Soret`, DN, `nAccepted` | ⚠ optional third panel; ⭐ `nAccepted` collapsing is otherwise invisible forever |
| ⛔ NOT raw spectra per row | §15.3 — they are not persisted, and they would dwarf the file |

### ⭐ 18.3 THE VIEW MODEL — generic, like everything else at this boundary

```
   SeriesPlotView(title, xLabel="minutes", panels=[...])
       panel(key, label, scale="linear" | ⭐ "log", autoscale=True)   ⭐ per-panel — §18.7 found this
       addSeries(panel, key, label, xs, ys, colour)     ⭐ plain numbers; the host interprets nothing
       addLevel (panel, y, label, style)                the threshold / the domain band
       addMarker(panel, x, label)                       ⭐ vertical event: "gate fired", "re-clouded"
       addPoint (panel, x, y, label)                    ⭐ the latched answer
       shownInReport = True                             M2's per-view flag -> it enters the PDF
```

⛔ **It must not be `SpectrumPlotView` with minutes smuggled in as nanometres.** That lie would surface
as a wavelength axis in the PDF and in every renderer that touches it.
⭐ The plugin builds it **from its own `MonitorRecord`** (§15.2) — `columns` gives the labels, `rows` the
numbers, `answer` the point. ⇒ the host still never learns what `Q%` is.

### 18.4 Where the step lives, and when it does not exist at all

| | |
|---|---|
| phase | ⭐ **PROCESSING** — it is *provenance of the measurement*, beside the Reference/Sample images and the spectra overlay, not a verdict |
| selection | ⭐ declared like any other step; the operator never lands on it during acquisition, exactly as Edwin asked |
| ⭐ when there is no record | ⛔ **the step is not declared at all** — a plain-burst plugin (§10.6) has no trajectory, and an empty graph would be worse than a missing tab. Same convention as "a hook that creates no steps is auto-skipped" |
| PDF | `shownInReport = True`; M2 renders it with the matplotlib path |

### ⚠ 18.5 Three honest caveats

⚠ **The saved graph is COARSER than the one that was watched.** The live view draws every row (~1.4 Hz);
only **decision rows** are persisted (§15.2). ⇒ a 2.5-minute product run yields a graph of **4–6 points**.
⭐ Draw markers *and* a connecting line, and ⛔ never smooth it — five points honestly drawn beat a smooth
curve implying data that was thrown away.

⚠ **A product-mode run's `Q%` panel is nearly featureless** — it stops at the read, by design (§12.2).
That is not a defect: the panel's job there is to show *that the fill was already flat*, which is exactly
what a short, level trace says. ⭐ The rich curve is the diagnostic mode's (§11.9c).

⚠ **Two renderers, not one.** A new view type costs an on-screen renderer *and* a matplotlib one for the
PDF (M2 is matplotlib-only). ⭐ That is the real price of §18, and it is worth paying once for a view that
serves live display, diagnosis and the report — ⛔ but it should not be paid twice by inventing a
separate "history" view later.

### ⭐ 18.6 What it unlocks beyond diagnosis

⭐⭐ **A `Q%` in a report that carries its own settling curve is a different object from a bare number** —
it shows the reader that the value was *chosen*, when, and on what evidence. §16.34.3d made that choice
load-bearing for the σ_fill story; ⭐ this is where it becomes visible to someone who was not in the room.

### ⭐⭐ 18.7 WHAT IT ACTUALLY LOOKS LIKE — and two rendering decisions the mock exposed  *(Edwin, 2026-08-17)*

⚠ ASCII here by request; ⭐ a pixel-accurate mock belongs in **wireloom** before it is built
(`DEV_WORKFLOW.md`, "Mock before you build").

#### The anatomy — three bands, and the top and bottom ones are not decoration

```
   HEADER    outcome · branch · how it was read · the answer · duration · clearing time
   PANELS    Q% (linear, autoscaled)  +  A_valley (⭐ LOG)  [+ optional health strip]
   FOOTER    W, j, k_gate, cadence, caps · evaluator id+version · exposure · inset
```

⭐ The footer is what makes a saved run **re-analysable in a year** (§15.2); ⛔ a graph without it is a
picture, not a record.

#### A · PRODUCT RUN — bath-cleared, arrived clear, stops at the read

```
┌ Settling ──────────────────────────────────────────────────────────────────────┐
│ ✅ SETTLED_IMMEDIATE   ·  the fill arrived clear  ·  read as FIRST_SETTLED_WINDOW│
│    Q% 13.30   at 2:02   ·  4 windows  ·  2:22 total  ·  clearing 0:00   ✓in domain│
├────────────────────────────────────────────────────────────────────────────────┤
│ Q%     13.40 ┤   •                                                             │
│              │        •       •                                                │
│        13.30 ┤                       ●  ⭐ the answer                           │
│        13.20 ┤                                                                 │
├──────────────┼─────────────────────────────────────────────────────────────────┤
│ A_valley     │                                    ⭐ gate fired 2:02            │
│  (log) 0.030 ┤   •    •       •       •                                  ┊     │
│        0.010 ┤ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  |rate| < 0.0017/min ┊     │
│              └───┬────────┬───────┬────────┬───────────────────────────────────│
│                 0:17     0:52    1:27     2:02                          minutes│
├────────────────────────────────────────────────────────────────────────────────┤
│ W 50 · j 2 · k_gate 2 · cadence 1/frame · cap 25:00 · dev-clearing v1.0         │
│ exposure 150 (pinned) · inset 1/3 · reference age 0:31                         │
└────────────────────────────────────────────────────────────────────────────────┘
```

⚠ **Four points is what a good run looks like**, and that is the honest picture (§18.5). ⭐ It says the
one thing it needs to: *the fill was flat from the first window, so there was nothing to wait for.*

#### B · DIAGNOSTIC RUN — a §11 arm: answer latched early, 20 minutes of photodamage after it

```
│ Q%     13.80 ┤                                              • •• •  •          │
│              │                                    • •• •  •                    │
│        13.55 ┤                         • • • ••          ── fit  +1.24 Q%/h    │
│              │            • •• • •                                             │
│        13.30 ┤ • ●• •       ⭐ answer 13.30 @ 2:02 — ⛔ LATCHED (§14.6)          │
│              └─┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────────────────────│
│                0    2.5    5    7.5    10   12.5   15   17.5   20      minutes │
│ A_valley (log) ┤ flat throughout, 0.028 -> 0.026        ⭐ gate fired 2:02      │
```

⭐⭐ **This single panel is §11's whole readout**: `Q%(t₀)` is the marked point, the photodamage slope is
the fitted line, and the flat `A_valley` proves the bath did its job before insertion.
⛔ Note the answer does **not** move when later rows dip below it — that is §14.6's latch, visible.

#### C · THE RE-CLOUDING CASE (§14.5) — and the only view in which it is legible

```
│ A_valley       │        ⚠ re-clouded — the jar entered colder than its cloud point│
│  (log)  0.20 ┤      • ••                                                        │
│         0.10 ┤    •      ••                                                     │
│         0.05 ┤   •          ••                        ⭐ gate fired 7:34         │
│         0.03 ┤ ••              • • • • • • • • • • • •┊• • • •                   │
│              └──┬─────┬─────┬─────┬─────┬─────┬─────┬─┊───┬────────────────────│
│                 0     1     2     3     4     5     6   7   8          minutes │
│ clearing 7:34  ·  ⚠ TEST B reset the gate twice  ·  Q% answer 13.44 @ 7:34     │
```

⭐ Without this panel the run above is indistinguishable from a slow one — the operator would only see
"it took 7 minutes". ⚠ And `clearingSeconds = 7:34` is exactly the σ_fill term §2.4 asked to be logged.

#### ⛔⛔ RENDERING DECISION 1 — the DOMAIN BAND CANNOT BE DRAWN AS AXIS LEVELS

§18.2's sketch put the 12–22 domain lines on the `Q%` panel. ⛔ **Drawing them forces the axis to span 10
units while the data varies by 0.5** — the trajectory collapses to a flat line and the panel says
nothing. ⇒ ⭐ **autoscale `Q%` to the data**, and carry the domain as a **status chip in the header**
(`✓ in domain`); draw an edge only when the value is actually near or outside it.

#### ⛔⛔ RENDERING DECISION 2 — THE GATE PANEL WANTS A LOG AXIS

`A_valley` falls **0.9455 → 0.0257**, a factor of 40. ⛔ On a linear axis the entire settling tail — the
part the gate is judging — lives in the bottom 3 % of the panel and the flattening is invisible. ⇒ ⭐
**log y for the gate panel, linear for `Q%`.** ⚠ Which means `SeriesPlotView` needs a **per-panel axis
scale** (§18.3), a field the first draft did not have.


### ⭐⭐ 18.8 SUB-TABS — yes, and the cut matters more than the idea  *(Edwin, 2026-08-17)*

⭐ **Zero new machinery**: `TabGroupView` already ships and this very plugin already uses it (the
Reference/Sample rasters group *Full frame* / *Cropped ROI*). ⇒ the Settling step declares one.

#### ⛔ THE RULE THAT DECIDES THE CUT — the first tab must answer the question ALONE

⛔⛔ **Do NOT split by quantity** (`Q%` | `A_valley` | `health`). It looks tidy and it destroys the
reading: judging an answer means seeing **where the gate fired relative to the `Q%` trace**, and those
two live on one screen or the judgement takes two clicks and a memory.
⇒ ⭐ **cut by QUESTION, not by variable.** Depth goes behind tabs; the reading never does.

```
 ┌ Settling ────────────────────────────────────────────────────────────────┐
 │ [ Overview ] [ Health ] [ Decisions ]                                    │
 ├──────────────────────────────────────────────────────────────────────────┤
 │  the §18.7 header + Q% panel + A_valley panel + the audit footer          │
 └──────────────────────────────────────────────────────────────────────────┘
```

| tab | holds | when it earns its place |
|---|---|---|
| ⭐ **Overview** *(default)* | header · `Q%` · `A_valley` · audit footer — ⭐ **exactly §18.7** | always. ⭐ It alone answers "what is the value and why was it read there?" |
| **Health** | `A_Soret`, DN, `nAccepted` per row | ⭐ this is what sub-tabs BUY: §18.2's "optional third panel" stops competing for space on the main reading |
| ⚠ **Decisions** | the numeric rows: `t`, `n/nAccepted`, `A_valley`, `rate(k,k−2)`, TEST A pass?, TEST B trend, counter, `Q%` | ⭐ answers "**why exactly there?**" numerically — ⚠ but see the cost below |

⛔ **No "Audit" tab.** The policy/evaluator/exposure line is a **record**, and a record behind a tab is a
record nobody reads. It stays as the Overview's footer.

#### ⚠ THE COST OF "DECISIONS" — it needs a second new view type

There is **no table view** in `plugin_sdk` today (the vocabulary is `MetricFieldView`, `LabelView`,
`SpectrumPlotView`, `VerdictGaugeView`, `TabGroupView`, …). ⇒ *Decisions* means a generic `TableView`.

⭐ **But the fit is unusually clean:** §15.2's `MonitorRecord` is already
`columns[{key,label,unit}] + rows[{key: value}]` — ⭐ **a self-describing table**. A generic `TableView`
renders any plugin's record with no plugin-specific knowledge, which is the same boundary §15.2 and
§18.3 already hold. ⇒ ⭐ worth building, ⚠ but **phased after** Overview and Health: the plots answer the
question, the table only sharpens it.

#### ⛔⛔ AND SUB-TABS FORCE A DECISION ABOUT THE PDF — tabs do not exist on paper

A `TabGroupView` is an *interaction*; a report is **linear**. ⇒ in the PDF the group must **flatten into
titled sections**, in tab order, and therefore:

```
   ⭐ per-TAB shownInReport, not just per-view
        Overview    always in the report
        Health      ⭐ only when it says something — the PLUGIN decides at build time
                       (a tripped DN guard, nAccepted collapsing, A_Soret near the floor)
        Decisions   ⚠ diagnostic runs only; 34 rows of table is not a customer-facing page
```

⭐ **That conditional inclusion is entirely plugin-side** and needs no host support — the plugin builds
the views, so it simply does not add the tab when there is nothing to say. ⇒ a clean report by default,
a full one when something went wrong, and ⛔ never a page of empty diagnostics in a miller's PDF.

---

## ⭐⭐ 19 · IMPLEMENTATION RUBBER-DUCK — walked against the AS-IS code  *(2026-08-17)*

> ⚠ In the style of `SPEC_capture_quality.md` §17.6. ⛔ Not a design review — §17 did that. This asks
> only: *what will actually bite when someone types this in?* Every finding below was checked against
> the code, not remembered.

### ⛔⛔ I1 — A LATENT MEMORY BLOW-UP ALREADY IN `CapturePanel`, WHICH LONG RUNS DETONATE

`CapturePanel.__capture`'s provider does this, today:

```python
   images.append(image)                                  # EVERY frame, kept
   ...
   self.__representativeFrames[role] = images[len(images) // 2]     # ...to pick ONE
```

⚠ Harmless at 60 frames. ⛔ **At a 20-minute monitored run that is ~1700 QImages of 2592×N RGB — on the
order of a gigabyte**, accumulated to choose a single middle frame.
⇒ ⭐ **The monitored path must never build that list.** Keep one frame — ideally the frame at the
**promoted answer window** (§9.1a), which is also more honest than "the middle one".
⛔ This is the single most likely way a first implementation dies on the rig, and it is in code that
exists and works today.

### ⛔ I2 — DO NOT BUMP `SDK_VERSION`. The instinct is wrong here.

`plugin_sdk/version.py`: `SDK_VERSION = 1`, and `checkSdkCompatibleVersion` demands **strict equality**
("Bump ONLY on a breaking change"). Adding `createMonitor()` with a default that returns `None` is
**additive** — every existing plugin keeps working.
⛔ **Bumping would break every DB-served, sealed plugin** (`SPEC_plugin_distribution.md` M3) with
*"rebuild the plugin"*, for an API none of them use. ⇒ ⭐ **no bump**, and the additive default is what
buys that.

### ⭐ I3 — THE REDUCE IS ALREADY WRITTEN, TWICE — extract, do not re-implement

| what the engine needs | what already exists |
|---|---|
| build a window Spectrum from k frames | ⭐ `Spectrum.addToCapturedValuesByNanometers()` — the frames list is a first-class field |
| mean it with C1 rejection | ⭐ `MeanSpectrumLogicModule` (core, Qt-free) already does exactly this |
| count survivors | ⚠ `SpectralWorkflowEngine.__survivingFrameCount` **already stacks frames and calls `rejectDimFrames`** |

⇒ ⭐ `MonitorEngine.reduce()` is ~5 lines over shipped code. ⚠ And `__survivingFrameCount` should be
**extracted into the SDK part** rather than left duplicated — it is the same computation.

### ⛔ I4 — C3's TOP-UP DOES NOT SURVIVE TRANSLATION LITERALLY, AND THE EQUIVALENCE TEST CAN MISS IT

`__runBurst` keeps grabbing until `frames` frames **survive C1** (`maxFrames = target + max(5, target//5)`).
A ring has no "top-up" — it is simply the last `W`. ⇒ `BurstEvaluator.decide()` must express C3 as
**"STOP when `nAccepted >= N`"**, not "when N frames were offered".
⚠ **A synthetic equivalence test on clean frames passes either way.** ⇒ ⭐ the test MUST include dim
frames — and `tests/test_capture_frame_rejection.py` already builds exactly that fixture.

### ⭐ I5 — THE EXISTING TESTS ARE THE EQUIVALENCE HARNESS. Do not rewrite them.

`tests/test_frame_provider_burst.py` and `tests/test_capture_frame_rejection.py` pin today's burst
through the very seam the monitor replaces. ⇒ ⭐ **the cheapest possible proof of §10.6 is that both
pass unchanged** once `captureAcquisitionStep` delegates. ⛔ Editing them to suit the new path would
throw away the only independent check there is.

### ⚠ I6 — TWO PIECES OF `CapturePanel` STATE THAT A MONITORED RUN MUST RESPECT

| | |
|---|---|
| capturing REFERENCE **clears the SAMPLE step's container** (an exposure re-lock invalidates it) | ⭐ it must clear the **`MonitorRecord` and the Settling tab** too, or a stale curve outlives its measurement |
| `__applyExtendedRoi` runs once, on the first frame, via a `state` dict | ⚠ must stay once-per-run — ⛔ not once per window |

### ⚠ I7 — SMALL THINGS THAT ARE CHEAP NOW AND ANNOYING LATER

- ⭐ **No Alembic migration is expected**: `MonitorRecord` rides inside the workflow's JSON blob
  (`SPEC_workflow_persistence.md`). ⚠ Verify before assuming; if it needs a column, the phase order
  changes.
- ⚠ **Rows are a LIST of dicts** with `t` as a *value* — ⛔ never a dict keyed by float (the known
  persistence gotcha).
- ⚠ `ApplicationStatusSignal` carries `stepsCount` / `currentStepIndex`; ⭐ verify the status widget
  renders `stepsCount = 0` as busy rather than as `0 / 0`.
- ⚠ `android/server/app_src/.../plugin_sdk` is a **checked-in stale copy** (no `SpectrumPlotView`, no
  `policy/`). ⛔ Do not sync it as part of this work — the drift predates it; just do not add to it.
- ⭐ Cancel needs **no forced `loop.quit()`**: `__pumpFrames`' nested loop already exits on its own
  timer, so the flag is seen on the next provider call. The existing `finally:` block already restores
  `__capturing`.

---

## ⭐⭐ 20 · IMPLEMENTATION PHASES

```
┌──────┬────────────────────────────────────────────┬──────────────────────┬──────────────────────────────────────────────┬───────────┐
│ PH   │ deliverable                                │ repos                │ gate (how it is known to be done)             │ needs     │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P0   │ ⭐ Cancel + hard caps on TODAY's burst      │ spectracsPy          │ a 60-frame capture stops mid-run; step stays  │     —     │
│      │   flag -> provider sentinel; maxSeconds/    │  (engine, panel,     │ uncaptured; ⛔ maxSeconds cannot be None;      │           │
│      │   maxFrames; outcome set (§12)              │   status bar)        │ existing burst tests still pass               │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P1   │ SDK PARTS (Qt-free): FrameRing,             │ spectracsPy-core     │ ⭐ fake evaluator drives a synthetic curve —   │    P0     │
│      │   MonitorEngine, BurstEvaluator,            │                      │ the engine names no wavelength; centre-stamp   │           │
│      │   Row/Decision/MonitorResult, MonitorPolicy │                      │ + latch + caps unit-tested; ⛔ no SDK bump     │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P2   │ PLUGIN: public monitorMetrics(),            │ spectracs-plugins    │ ⭐⭐ decide() replayed on the 2026-08-14 CSV    │    P1     │
│      │   ClearingEvaluator (TEST A + TEST B,       │                      │ rows fires at t≈16.7 and reads 13.27 (§14.3); │           │
│      │   j=2, latch, branches), createMonitor()    │                      │ ⛔ no private-name access left in the script   │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P2b  │ ⭐ UNIFY: captureAcquisitionStep delegates   │ spectracsPy          │ ⭐⭐ tests/test_frame_provider_burst.py AND     │    P1     │
│      │   to MonitorEngine + BurstEvaluator (§10.6) │                      │ test_capture_frame_rejection.py pass          │           │
│      │   ⚠ C3 as nAccepted>=N (I4)                 │                      │ UNCHANGED (I5) — incl. the dim-frame fixture  │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P3   │ SCRIPT onto the plugin: createMonitor +     │ spectracsPy          │ same CLI/CSV; ⭐ +n and both timestamps;       │    P2     │
│      │   offer(); --npz; diagnostic stop policy;   │  (diagnostics/)      │ ⚠ profile installed into the app context so   │           │
│      │   app-tier frame extraction (§10.7b)        │                      │ inset = 1/3; baseline CSV re-derives verdict   │           │
├══════┼════════════════════════════════════════════┼══════════════════════┼══════════════════════════════════════════════┼═══════════┤
│ P4   │ ⭐⭐ §11 THE HEAT-DOSE EXPERIMENT            │ ⛔ NO CODE — the rig │ 4 arms x 20 min, identical arcs, pre-warmed;  │    P3     │
│      │   arms a/b/c(+d), pre-registered rule       │                      │ the decision rule of §11.5 is applied as-is   │           │
├══════┼════════════════════════════════════════════┼══════════════════════┼══════════════════════════════════════════════┼═══════════┤
│ P5   │ HOST: captureMonitoredStep, legend box,     │ spectracsPy          │ click-through; ⛔ I1 fixed (ONE representative │  P2b, P4  │
│      │   indeterminate status bar, coach lines,    │                      │ frame, not a list); reference re-capture      │           │
│      │   U2/U3 messages                            │                      │ clears the record too (I6)                    │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P6   │ PERSISTENCE: generic MonitorRecord on the   │ spectracsPy          │ a saved run re-opens and redraws; ⭐ rows are  │    P5     │
│      │   workflow (columns/rows/answer, §15.2)     │  (+ -model if any)   │ a LIST (no float keys); ⚠ expect NO migration │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P7   │ SeriesPlotView (per-panel scale, log) +     │ core/-model,         │ ⭐ built ONCE, used 3x: live trace, Settling   │    P6     │
│      │   Settling step [Overview|Health] + PDF     │ plugins, spectracsPy │ tab, PDF page; tabs FLATTEN to sections;      │           │
│      │   flattening + per-tab shownInReport        │                      │ Health omitted when it has nothing to say     │           │
├──────┼────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────────┼───────────┤
│ P8   │ ⚠ OPTIONAL, LAST: generic TableView +       │ core/-model,         │ renders any plugin's MonitorRecord with no    │    P7     │
│      │   the [Decisions] sub-tab (§18.8)           │ spectracsPy          │ plugin-specific knowledge                     │           │
└──────┴────────────────────────────────────────────┴──────────────────────┴──────────────────────────────────────────────┴───────────┘

   ⭐ P0..P3 is the whole critical path to the experiment — no host, no persistence, no UI.
   ⭐ P2b can land in parallel with P2/P3; it is what earns cancel for every plugin (§12.1).
   ⛔ P5 must not start before P4: a coach line tuned against a read rule the experiment may change
      is work done twice.
```

⛔ **CORRECTION to the "needs" column** *(Edwin's question, 2026-08-17)*: **P1 does not need P0.** P0 is
cancel in the *app's* capture panel; the script has its own loop and its own Ctrl-C, and the engine's
hard caps arrive with P1 itself. ⇒ ⭐ **the experiment's true critical path is P1 → P2 → P3 → P4**, and
**P0 is independent** — worth doing (it is small and needed anyway) but it blocks nothing.

### ⭐⭐ 20.1 WHAT P3 ACTUALLY IS — the script on the real plugin  *(Edwin: "the P3 script already would use the new DEV plugin?")*

⭐ **Yes. That is the whole content of P3** — P2 exists precisely so P3 has something to call:

```python
   monitor = DevSpectralPlugin().createMonitor(reference, mode=DIAGNOSTIC)   # ⭐ P2's deliverable
   while not monitor.isFinished():
       image = backend.read()                       # ⭐ the SCRIPT's camera, exposure PINNED
       row = monitor.offer(frameSpectrum(image), time.time())
       if row: csv.writerow(row); print(row)
```

| P3 changes in the script | why |
|---|---|
| ⛔ delete `metricsOf`, `clearingDone`, `vertexRead`, `settledYet`, `zeroDoseEstimate` | ⭐ they all move into the plugin's `ClearingEvaluator` — this is the DRY payoff, and the private `__vTerms` access dies with them |
| swap `captureMean`'s own decode for the **app's** per-frame extraction | §10.7b — inset 1/3, and a `SpectrometerProfile` installed into the app context first |
| ⭐ capture the REFERENCE through `MonitorEngine + BurstEvaluator` too | ⭐ then **both** captures in the run go through the one path, and the script exercises P2b's equivalence claim by simply working |
| `--npz` + the `n` and dual-timestamp columns | §11.8a, §10.7c |
| ⭐⭐ **flush on `KeyboardInterrupt`** | ⛔ otherwise Ctrl-C on minute 15 of a 20-minute arm throws the arm away. The CSV and the `.npz` must be written from a `finally:` |

⚠ **What P3 does NOT need:** P2b (the host's unification), P5 (the GUI), P6 (persistence). ⭐ The script
reaches the experiment with **no app changes at all** beyond what P1/P2 put in the SDK and the plugin.

---

## ⭐⭐ 21 · SECOND IMPLEMENTATION RUBBER-DUCK — the MECHANICS of writing it  *(Edwin, 2026-08-17: "this is a rather large code change")*

> ⚠ §19 asked *what will bite*. This asks *in what order does one type it, and what does the codebase
> refuse to allow?* — the §17.7 question. ⭐ Two of these are hard constraints discovered in the loader,
> not preferences.

### ⛔⛔ M1 — THE PLUGIN MUST REMAIN **ONE SELF-CONTAINED FILE**. This decides where the evaluator lives.

`PluginPublishUtil.lintSelfContained()` **rejects a plugin source that imports app or sibling code, or
uses a relative import** — a published plugin is a single module defining exactly one `SpectralPlugin`
subclass, `exec`'d by the loader (`SPEC_plugin_distribution.md` D-coderef).

```
   ⛔ plugins/dev/ClearingEvaluator.py, imported by DevSpectralPlugin   -> UNPUBLISHABLE
   ⭐ class ClearingEvaluator inside DevSpectralPlugin.py               -> fine: the lint forbids
      (a plain class — NOT a SpectralPlugin subclass, or "more than         sibling IMPORTS, and
       one plugin class" trips a different check)                           allows extra classes
```

⭐⭐ **AND THE COROLLARY THAT IS EASY TO MISS:** the evaluator may import **only from `plugin_sdk`.** ⇒
`FrameRing`, `MonitorEngine`, `BurstEvaluator`, `MonitorPolicy`, `Row`, `Decision` **must be exported
from `plugin_sdk/__init__.py` and listed in `__all__`** — otherwise the plugin physically cannot reach
the parts it is supposed to compose. ⛔ Omit that and P2 fails at the lint, not at runtime.
⚠ Cost accepted: `DevSpectralPlugin.py` grows from **1157** to roughly 1300 lines. There is no
alternative that keeps the plugin publishable.

### ⛔ M2 — DO NOT EDIT `reference_drift_probe._spectrum`. Three scripts share it; two published on it.

`clearing_time_course.py`, `cuvette_reseat_probe.py` and `ring_probe.py` all import it, and the app
module's own comment records that the 0.2 inset is frozen **on purpose** to reproduce published numbers
(§10.7b). ⇒ ⭐ P3 adds a **parallel** helper (`appFrameSpectrum()`, inset 1/3, app-tier extraction) used
by the settling script alone. ⛔ Changing the shared one silently re-bases two other diagnostics.

### ⚠ M3 — `__vTerms` RETURNS `None`, AND THAT SHAPES THE `Row`

The guard is inside the metric: `__vTerms` yields `None` when `A_Soret < 0.15`. ⇒ a `Row` must be able
to carry **no values at all** — ⭐ which is exactly what `BurstEvaluator`'s row already looks like
(spectrum, no metrics). ⇒ **one Row shape serves both**, the engine never inspects `values`, and
`decide()` maps `None` → `MEASUREMENT_BROKEN`. ⛔ An engine that assumes `row.values["qPercent"]` exists
crashes on the first broken fill.

### ⭐⭐ M4 — THE WRITE ORDER THAT KEEPS THE TREE GREEN AT EVERY COMMIT

```
   1  SDK parts + their unit tests            nothing calls them      -> ⭐ zero behaviour change
   2  plugin_sdk/__init__ exports + __all__   (M1's corollary)        -> ⭐ zero behaviour change
   3  monitorMetrics() PUBLIC on the plugin,
      and ⭐ __vTerms DELEGATES TO IT          one definition, moved   -> ⭐ zero behaviour change
   4  ClearingEvaluator + createMonitor()     still unused by the app -> ⭐ zero behaviour change
   5  the SCRIPT onto the plugin              ⚠ FIRST behaviour change — and it is in a DIAGNOSTIC
   6  P2b: the engine delegates               ⛔ the only change to SHIPPED capture behaviour
```

⭐ **Five of the six steps cannot break the app**, because nothing in it calls the new code yet. ⇒ the
large change is large in *volume*, not in *risk* — provided this order is kept.
⛔ Step 3's direction matters: `__vTerms` must call the new public method, **never the reverse**. Two
copies of the metric existing "for a while" is precisely the §10.1a failure, in miniature.

### ⚠ M5 — P2b IS THE ONLY STEP WITH A ROLLBACK QUESTION

⭐ Keep `captureAcquisitionStep`'s **exact return contract** (the accumulated `Spectrum`, or `None`) —
the monitored variant is a **different method**, not a changed signature, or `test_frame_provider_burst`
stops being an equivalence check.
⛔ **Do not ship a feature flag** with the old `__runBurst` kept alongside: dead code that two paths must
be kept honest against is worse than a revert. ⭐ One commit, two existing tests as the gate, `git revert`
as the rollback.

### ⚠ M6 — SMALL MECHANICS, EACH CHEAP NOW

- ⭐ `createMonitor(reference, mode=PRODUCT)` — a **defaulted** parameter, so an M3-sealed plugin built
  against today's signature keeps loading (with §19/I2: still no `SDK_VERSION` bump).
- ⚠ In the script, the `SpectrometerProfile` install must happen **before the first frame is extracted**,
  because the app-tier extractor reads calibration from the context singleton at call time.
- ⚠ Churn map: `-core` +5 small files · `-plugins` +~150 lines in one file · `spectracsPy` engine (226 l)
  +1 method, `CapturePanel` (878 l) touched by P0 and P5 · `diagnostics/` one script rewritten.
- ⭐ Nothing imports `clearing_time_course`'s helpers (checked) — deleting `metricsOf`, `clearingDone`,
  `vertexRead`, `settledYet`, `zeroDoseEstimate` breaks no other diagnostic.

---

## ⭐⭐ 22 · IMPLEMENTATION PHASES — revised after the second pass

```
┌──────┬─────────────────────────────────────────────┬───────────────────┬─────────┬──────────────────────────────────────────┬─────────┐
│ PH   │ deliverable                                 │ repo / file       │ app be- │ gate                                     │ needs   │
│      │                                             │                   │ haviour │                                          │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P1a  │ FrameRing · MonitorEngine · BurstEvaluator   │ -core             │  none   │ ⭐ a FAKE evaluator drives a synthetic     │    —    │
│      │ Row · Decision · MonitorResult · Policy      │ plugin_sdk/       │         │ curve: centre-stamp, latch, caps, cadence│         │
│      │ ⭐ extract __survivingFrameCount here (I3)   │  acquisition/     │         │ ⛔ engine names no wavelength             │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P1b  │ ⛔ export the parts in __init__ + __all__    │ -core             │  none   │ ⭐ M1: a plugin source importing ONLY     │   P1a   │
│      │    (M1's corollary — else the lint fails)    │ plugin_sdk/       │         │ plugin_sdk passes lintSelfContained()    │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P2a  │ monitorMetrics() PUBLIC;                     │ -plugins          │  none   │ existing plugin tests unchanged;         │   P1b   │
│      │ ⭐ __vTerms DELEGATES to it (M4/3)           │ DevSpectralPlugin │         │ ⛔ exactly ONE definition of the metric   │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P2b  │ class ClearingEvaluator (TEST A + TEST B,    │ -plugins          │  none   │ ⭐⭐ decide() replayed on the 2026-08-14   │   P2a   │
│      │ j=2, latch, branches, coach) + createMonitor │ ⛔ SAME FILE (M1) │         │ CSV rows fires t≈16.7, reads 13.27       │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P3   │ SCRIPT on the plugin: createMonitor+offer;   │ spectracsPy       │ ⚠ diag  │ same CLI/CSV +n +2 timestamps; ⭐ flush   │   P2b   │
│      │ --npz; DIAGNOSTIC mode; appFrameSpectrum     │ diagnostics/      │  only   │ on KeyboardInterrupt; baseline CSV       │         │
│      │ (M2: parallel helper, ⛔ not the shared one) │                   │         │ re-derives the same verdict              │         │
├══════┼═════════════════════════════════════════════┼═══════════════════┼═════════┼══════════════════════════════════════════┼═════════┤
│ P4   │ ⭐⭐ §11 THE HEAT-DOSE EXPERIMENT             │ ⛔ NO CODE — rig  │    —    │ 4 arms × 20 min, identical arcs,         │   P3    │
│      │                                             │                   │         │ pre-warmed; §11.5's rule applied as-is   │         │
├══════┼═════════════════════════════════════════════┼═══════════════════┼═════════┼══════════════════════════════════════════┼═════════┤
│ P0   │ ⭐ Cancel + hard caps on TODAY's burst        │ spectracsPy       │  ⚠ YES  │ a 60-frame capture stops mid-run; step   │  ⭐ none │
│      │ (INDEPENDENT — blocks nothing)               │ engine + panel    │         │ stays uncaptured; ⛔ maxSeconds ≠ None    │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P5   │ ⛔ UNIFY: captureAcquisitionStep delegates    │ spectracsPy       │ ⛔ YES — │ ⭐⭐ test_frame_provider_burst.py AND      │ P1a,P0  │
│      │ to MonitorEngine+BurstEvaluator; C3 as       │ engine            │ the ONE │ test_capture_frame_rejection.py pass     │         │
│      │ nAccepted≥N (I4); ⛔ no feature flag (M5)     │                   │  step   │ UNCHANGED, incl. the dim-frame fixture   │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P6   │ HOST: captureMonitoredStep · legend box ·    │ spectracsPy       │  ⚠ YES  │ click-through; ⛔ I1 fixed (ONE frame,    │ P5, P4  │
│      │ indeterminate bar · coach/U2/U3 messages     │ panel + views     │         │ not a list); ref re-capture clears the   │         │
│      │                                             │                   │         │ record (I6)                              │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P7   │ PERSISTENCE: generic MonitorRecord on the    │ spectracsPy       │  ⚠ YES  │ a saved run re-opens and redraws; rows   │   P6    │
│      │ workflow (columns/rows/answer)               │ (+ -model if any) │         │ are a LIST; ⚠ expect NO migration        │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P8   │ SeriesPlotView (per-panel log scale) +       │ -core/-model,     │  ⚠ YES  │ ⭐ ONE view, three uses; tabs FLATTEN to  │   P7    │
│      │ Settling step [Overview|Health] + PDF        │ -plugins, Py      │         │ PDF sections; Health omitted when empty  │         │
├──────┼─────────────────────────────────────────────┼───────────────────┼─────────┼──────────────────────────────────────────┼─────────┤
│ P9   │ ⚠ OPTIONAL, LAST: generic TableView +        │ -core, Py         │  ⚠ YES  │ renders any plugin's MonitorRecord with  │   P8    │
│      │ the [Decisions] sub-tab                      │                   │         │ no plugin-specific knowledge             │         │
└──────┴─────────────────────────────────────────────┴───────────────────┴─────────┴──────────────────────────────────────────┴─────────┘

  ⭐⭐ READ THE "app behaviour" COLUMN: P1a..P2b change NOTHING that runs today. The critical path to
     the experiment (P1a -> P1b -> P2a -> P2b -> P3 -> P4) touches the shipped app in ⭐ NO place at all.
  ⭐ P0 and P5 are the only steps that alter existing capture, and P5 is gated by two tests that
     already exist and must pass UNCHANGED.
  ⛔ P6 must not start before P4 — a coach line tuned against a read rule the experiment may still
     change is work done twice.
```

---

## ⛔⛔ 23 · THIRD IMPLEMENTATION RUBBER-DUCK — and it found a PREREQUISITE, not a detail  *(2026-08-17)*

### ⭐⭐ V1 — ✅ **MEASURED AND CLOSED, 2026-08-17 — from data that was already on disk**

> ⛔ The finding below was written as a blocking prerequisite ("an afternoon's logging"). ⭐ It took two
> minutes instead, because `captureDiagnostics/*.json` (the `SPECTRACS_LOG_SPECTRA` dumps) **already
> contain every per-frame spectrum** — `frames`, `kept`, `frameBrightness`, `rejectedCount`.

```
   11 REFERENCE dumps, 150 frames each      1430 frames   ->   1173 DISTINCT   =  82.0 %
   longest run of identical consecutive frames:  ⭐ 2      (never 3, in any dump)
```

⭐⭐ **So duplicates are REAL but MILD**: ~1 frame in 6 repeats its predecessor, and never more than
twice. Something does pace the provider — the pump is not free-running as the code reading suggested.

| consequence | |
|---|---|
| effective count | ⭐ `W = 50` behaves like **41 independent frames** |
| σ inflation | **× 1.10** |
| §14.2b's gate margin | 4.4 σ → ⭐ **4.0 σ** — comfortable; the conclusion is unchanged |
| the short-gate refutation | ⭐ **strengthened**: `W = 20` behaves like 16 |

⇒ ⛔ **V1 is NOT a prerequisite and P-1 is not a phase.** ⭐ What survives is a one-line *confirmation*:
these dumps are from **2026-07-20 at frameCount 150**, and the burst is now **60** (§ soret-448 S7). The
duplicate rate is a race between the 120 ms pump and the camera's frame period, so it moves with
**exposure**. ⇒ ⭐ re-run the same count on the next rig session — `SPECTRACS_LOG_SPECTRA=1`, one
capture, the analysis above — and fold the measured factor into `W` rather than assuming 1.00.
⚠ **And log the effective fraction in the `MonitorRecord`** (§15.2): a run whose duplicate rate drifted
is a run whose noise budget drifted with it.

### ⚠ V1-original — the reasoning that prompted the check *(kept: the mechanism is real, only its size was wrong)*

Walked through the delivery path, line by line:

```
   VideoThread            backend.read() blocks on the camera  ->  emits at ~1.0-1.5 fps (2592/USB2)
   handleVideoThreadSignal  self.__latestImage = videoSignal.image        (CapturePanel:423)
   the burst provider       __pumpFrames(120 ms); image = __latestImage.copy()   (CapturePanel:636-639)
                            ⛔ AND IT NEVER CLEARS __latestImage AFTERWARDS
```

⇒ ⛔ **between two camera frames (~700 ms) the provider is called ~6 times and can hand back the SAME
frame each time.** The one clearing (line 625) happens *once*, before the burst.

⚠ **The contradicting datum is Edwin's own:** *"50 frames takes say 50 seconds or longer."* ⭐ The
reconciliation is probably that the ~**15-second AE sweep** (line 454's comment: "the thread emits
NOTHING during the ~15 s sweep") plus ROI widening and settling dominate the **step**, while the burst
itself may indeed be ~7 s of mostly repeated frames.

⛔⛔ **WHY THIS IS NOT A CURIOSITY — three things in this spec rest on frame independence:**

| what assumes it | what breaks if frames repeat |
|---|---|
| ⭐ §14.2b's noise budget | `σ_A ∝ 1/√W` becomes `1/√(distinct)`. ⛔ At 6× duplication `W = 50` behaves like **W ≈ 8**, and θ drops from 4.4 σ to ~**0.7 σ** — the gate would be pure noise |
| C1 rejection | identical frames give **MAD = 0**, so rejection falls through to the `DIM_FRAME_SCALE_FLOOR` branch every time |
| ⚠ the whole archive's `√N` claim | the 0.063 no-re-seat floor is *measured*, so it stands — ⛔ but "more frames = less noise" would not be true above the real frame rate |

⭐⭐ **THE TEST IS FIVE MINUTES AND COSTS NOTHING:** log the `cacheKey()` (or the buffer address) of every
image the provider returns during one 60-frame burst and count distinct values.

```
   60 distinct   ->  ⭐ something paces the provider; find it and rely on it deliberately
   ~10 distinct  ->  ⛔ the provider must WAIT FOR A NEW FRAME (a sequence counter set in the
                        handler, checked in the provider) — and §14.2b's budget must be recomputed
                        against the REAL number, which may push W up or j up
```

⇒ ⛔⛔ **This becomes phase P−1: it precedes P1a**, because the SDK's window size and the gate's threshold
are both derived from a number this test either confirms or destroys.
⚠ And note what it would explain if duplicates are real: bursts that "average 60 frames" while behaving
like 8 is exactly the kind of hidden factor that makes floors look mysterious.

### ⚠ V2 — C1 WAS DESIGNED FOR AN ARTEFACT, AND A ROLLING WINDOW FEEDS IT A SIGNAL

`rejectDimFrames` drops frames whose brightness is a MAD-outlier **within the window** — built for the
coherent dim group an **auto-exposure ramp** leaves behind (§14.8).
⛔ **During fast clearing the brightness ramp inside a window is not an artefact — it is the measurement.**
A 35-second window early in a clearing run holds a genuine monotone rise, so C1 will preferentially
reject its **oldest and newest** frames and bias the mean toward the window's centre.

⭐ Consequences, none of them fatal:
- ⭐ `nAccepted` **will dip during fast clearing**, and that is CORRECT behaviour, not a fault — ⛔ the UI
  must not report it as one (§13.4's health line).
- ⚠ The centre-bias is mostly harmless because §9.3 already stamps the row at the window **centre** —
  ⭐ the two effects point the same way, which is luck rather than design, and worth writing down.
- ⛔ Do not "fix" C1 for this. It is right for the reference burst, which is where it earns its keep.

### ⚠ V3 — THE FRAME-DELIVERY HANDSHAKE MAKES ROW WORK THROTTLE THE CAMERA

`handleVideoThreadSignal` ends with `event.set()` — the video thread **waits for the GUI** to finish
handling each frame (`tests/test_video_signal_queued_delivery.py`). ⇒ every millisecond spent evaluating
a row is a millisecond the camera is not grabbing.
⭐ Harmless at §9.1b's few milliseconds. ⛔ It stops being harmless if P8's plotting is ever done inside
the row callback. ⇒ **plot from a timer, not from the row.**

### ⚠ V4 — TWO ASYMMETRIES BETWEEN THE BENCH RUN AND THE SCRIPT RUN, BOTH INTENDED

| | bench | script |
|---|---|---|
| AE sweep | ⚠ ~15 s at the start of a capture | ⛔ none — exposure pinned by `_pickExposure` (§10.7a) |
| consequence | the first window starts ~15 s after Measure | the first window starts immediately |

⇒ ⭐ `clearingSeconds` is measured **from the first offered frame**, not from the click — otherwise the
bench and the script would report clearing times that differ by the sweep, and §2.4 is trying to make
that number comparable across runs.

---

## ⭐⭐ 24 · IMPLEMENTATION PHASES — third revision

```
┌──────┬──────────────────────────────────────────────┬──────────────────┬─────────┬─────────────────────────────────────────┬─────────┐
│ PH   │ deliverable                                  │ repo / file      │ app be- │ gate                                    │ needs   │
│      │                                              │                  │ haviour │                                         │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ ✅   │ ~~FRAME-IDENTITY PROBE~~ — ⭐ ALREADY ANSWERED │  —               │  none   │ ⭐ 82 % distinct; W=50 ≙ 41 frames;      │  DONE   │
│ V1   │ from captureDiagnostics/*.json (§23/V1)      │                  │         │ σ × 1.10; gate margin 4.0 σ             │         │
│      │ ⚠ re-confirm at frameCount 60 on the next rig│                  │         │ session (one capture, same analysis)    │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P1a  │ ⭐ P1 = P1a + P1b, "THE SDK TIER"             │ -core            │  none   │ ⭐ FAKE evaluator on a synthetic curve;  │    —    │
│      │ FrameRing · MonitorEngine · BurstEvaluator · │ plugin_sdk/      │         │ centre-stamp · latch · caps · cadence;  │         │
│      │ Row · Decision · Result · Policy  (+I3)      │  acquisition/    │         │ ⛔ engine names no wavelength            │         │
│ P1b  │ ⛔ export the parts in __init__ + __all__ (M1)│ -core            │  none   │ ⭐ an sdk-only source passes             │  P1a    │
│      │                                              │                  │         │ lintSelfContained()                     │         │
│ P2a  │ monitorMetrics() PUBLIC; ⭐ __vTerms delegates│ -plugins         │  none   │ ⛔ exactly ONE definition of the metric  │  P1b    │
│ P2b  │ class ClearingEvaluator (TEST A + TEST B,    │ -plugins         │  none   │ ⭐⭐ decide() replayed on the 2026-08-14  │  P2a    │
│      │ j, latch, branches, coach) + createMonitor   │ ⛔ SAME FILE (M1)│         │ CSV rows → t ≈ 16.7, reads 13.27        │         │
│ P3   │ SCRIPT on the plugin; --npz; DIAGNOSTIC mode;│ spectracsPy      │ ⚠ diag  │ ⭐ flush on KeyboardInterrupt; baseline  │  P2b    │
│      │ appFrameSpectrum (M2); clearingSeconds from  │ diagnostics/     │  only   │ CSV re-derives the same verdict         │         │
│      │ the FIRST FRAME (V4)                         │                  │         │                                         │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P4   │ ⭐⭐ §11 THE HEAT-DOSE EXPERIMENT              │ ⛔ NO CODE — rig │    —    │ 4 arms × 20 min, identical arcs,        │  P3     │
│      │                                              │                  │         │ pre-warmed; §11.5's rule applied as-is  │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P0   │ ⭐ Cancel + hard caps on TODAY's burst        │ spectracsPy      │  ⚠ YES  │ a 60-frame capture stops mid-run;       │ ⭐ none  │
│      │ (INDEPENDENT — blocks nothing)                │ engine + panel   │         │ ⛔ maxSeconds ≠ None                     │         │
│ P5   │ ⛔ UNIFY: captureAcquisitionStep delegates;    │ spectracsPy      │ ⛔ THE  │ ⭐⭐ BOTH existing burst tests pass       │P1a,P0   │
│      │ C3 as nAccepted ≥ N (I4); ⛔ no flag (M5)      │ engine           │ ONE step│ UNCHANGED, incl. the dim-frame fixture  │         │
│ P6   │ HOST: captureMonitoredStep · legend box ·     │ spectracsPy      │  ⚠ YES  │ click-through; ⛔ I1 fixed (ONE frame);  │ P5, P4  │
│      │ indeterminate bar · U2/U3 · ⚠ plot from a    │ panel + views    │         │ ref re-capture clears the record (I6);  │         │
│      │ TIMER, not from the row callback (V3)        │                  │         │ nAccepted dip is NOT shown as a fault   │         │
│ P7   │ PERSISTENCE: generic MonitorRecord           │ spectracsPy      │  ⚠ YES  │ a saved run re-opens and redraws; rows  │  P6     │
│      │ (columns / rows / answer)                    │ (+ -model if any)│         │ are a LIST; ⚠ expect NO migration       │         │
│ P8   │ SeriesPlotView (per-panel log) + Settling    │ -core/-model,    │  ⚠ YES  │ ⭐ ONE view, three uses; tabs FLATTEN    │  P7     │
│      │ step [Overview|Health] + PDF flattening      │ -plugins, Py     │         │ to PDF sections                         │         │
│ P9   │ ⚠ OPTIONAL, LAST: TableView + [Decisions]     │ -core, Py        │  ⚠ YES  │ renders any plugin's record blind       │  P8     │
└──────┴──────────────────────────────────────────────┴──────────────────┴─────────┴─────────────────────────────────────────┴─────────┘

  ⭐ NAMING: there is no bare "P1" — ⭐ P1 = P1a + P1b (the SDK tier), P2 = P2a + P2b (the plugin tier).
  ✅ The frame-identity probe is CLOSED (§23/V1): 82 % distinct, so W=50 carries 41 independent frames
     and the gate keeps 4.0 σ. ⚠ One cheap re-confirmation at frameCount 60 rides the next rig session.
  ⭐⭐ P1a..P2b change NOTHING that runs today; the whole path to the experiment
      (P1a → P1b → P2a → P2b → P3 → P4) touches the shipped app in ⭐ no place at all.
  ⛔ P6 must not start before P4.
```

---

## ⭐⭐ 25 · FOURTH IMPLEMENTATION RUBBER-DUCK — three unexamined corners, one of them a spec ERROR  *(2026-08-17)*

> ⚠ §19 asked *what will bite*, §21 *in what order does one type it*, §23 *what must be verified first*.
> ⭐ This pass takes the three corners none of them entered: **the file format, the clock, and the test
> harness**. ⛔ It also retracts a claim made in §9.1a.

### ⛔⛔ X1 — `np.savez` CANNOT APPEND. §9.1a's "append as you go, RAM stays bounded" IS WRONG.

§9.1a says: *"Append-as-you-go and the re-windowing of §9.3 is still possible offline, with `R`
unchanged."* ⛔ **There is no append mode for `.npz`** — `np.savez_compressed` writes the archive once
and closes it. The claim is not merely awkward, it is impossible.

| ⭐ the fix, and it is the boring one | |
|---|---|
| ⭐ **accumulate the frames in RAM and write once, from `finally:`** | 20 min ≈ **34 MB** — nothing on a bench machine, and it is *already* the KeyboardInterrupt-flush P3 needs |
| ⚠ alternative if a run ever outgrows RAM | chunked `.npy` files in a directory, zipped at the end |
| ⛔ what must NOT be done | claim bounded RAM and then hold every frame anyway — which is what §9.1a currently promises |

⇒ ⭐ **`R` (retention) stays bounded for the ENGINE; the SCRIPT separately holds the whole run.** Those
are two different buffers with two different lifetimes, and §9.1a blurred them.

### ⛔ X2 — "EVERY W-th ROW" SILENTLY BREAKS THE MOMENT THE CADENCE CHANGES

§14.3's rule 1 says decisions use *every `W`-th row*. ⛔ With `evaluateEveryNFrames = 5`, rows are 5
frames apart, so "every 50th row" is **250 frames apart** — `j` is multiplied by 5 and nobody notices,
because the gate still *works*, only slower and with a different noise budget than the one §14.2b
derived.

```
   ⛔ decision row  :=  every W-th ROW                 depends on the cadence
   ⭐ decision row  :=  a row whose window's LAST FRAME INDEX ≡ 0 (mod W)
                        -> defined in FRAMES; cadence may change freely; j keeps its meaning
```

⚠ §9.1b explicitly reserves the right to raise the cadence if a row costs too much. ⇒ these two sections
are a trap for each other unless the definition is anchored in frames.

### ⚠ X3 — USE `time.monotonic()`. A 20-MINUTE RUN IS LONG ENOUGH TO BE HIT BY THE CLOCK.

§10.7's sketch passes `time.time()`. ⛔ Wall-clock can step (NTP correction, a DST change, a laptop
resuming): a backwards step makes `Δt` negative and the rate nonsense — ⚠ and a *near-zero* `Δt` makes it
enormous, which trips TEST B's re-clouding reset rather than failing loudly.
⇒ ⭐ **`time.monotonic()` for the trajectory, wall-clock recorded separately** as a human-readable stamp
(the CSV already prints `%H:%M`). ⚠ Free to get right now, invisible and unreproducible when wrong.

### ⚠ X4 — A MONITOR IS SINGLE-USE

⭐ Create one per capture; ⛔ never reuse across captures. A reused monitor carries a stale ring, a
**latched answer** (§14.6) and a reference that may no longer be the one on the bench (§19/I6).
⇒ cancel, failure and success all end with the object discarded — and the host asks the plugin for a
fresh one on the next Measure.

### ⚠ X5 — WHAT IF `evaluate()` RAISES ON ROW 900?

⛔ **Do not swallow it** — a silently-skipped row hides a plugin bug behind a slightly noisier curve.
⭐ End the run with outcome `FAILED`, surface the traceback (script: print it; host: the coach line) —
⭐⭐ **but still write the partial trajectory.** A fifteen-minute arm must not evaporate because the last
row raised.

### ⚠ X6 — TESTS MUST NEVER WAIT ON WALL-CLOCK, AND THE PUSH API IS WHY THEY DO NOT HAVE TO

`tests/conftest.py` arms a **120-second per-test faulthandler watchdog** (`SPEC_test_hygiene_debt.md`
T2). ⛔ A test that drives a monitor in real time is either useless (too short to settle) or a suite
hang.
⭐⭐ **And it is already solved by design:** `offer(frame, timestamp)` takes the clock as an argument
(§10.1), so a **90-minute clearing curve replays in milliseconds** with synthetic timestamps. ⇒ the unit
tests should *demonstrate* that — it is the clearest possible justification of the push seam.

### ⚠ X7 — `box_metrics.py` IS THE PRE-REGISTRATION RECORD. DO NOT REPOINT IT.

It deliberately freezes its own copy of the windows and the formula (the file says so). ⛔ Moving it onto
the new public `monitorMetrics()` would destroy the one artefact whose value is that it **cannot follow
the code** — the same rule as §21/M2 for `_spectrum`.

### ⚠ X8 — NUMERICAL GUARDS TO CARRY OVER, NOT REINVENT

⭐ The prototype already has them and they must survive the move into `ClearingEvaluator`: fewer than 3
points → return the raw row; `a <= 0` in the parabola fit → the vertex is a maximum, fall back; NaN band
means → no row. ⚠ `np.polyfit` on identical x, or on an all-NaN column, raises rather than returning
`nan` — ⛔ and that raise lands in X5's path at the worst moment.

### 25.1 ⚠ On the diminishing returns of a fifth pass

⭐ Passes 1–4 each found something real: a latent crash (I1), two hard loader constraints (M1), a closed
verification (V1) and a spec error (X1). ⚠ **A fifth pass over the same text would mostly re-read it.**
⇒ the next genuinely new information comes from **P1a's first unit test** — the first moment the design
has to survive contact with an interpreter.

---

## ⭐⭐ 26 · IMPLEMENTATION PHASES — fourth revision

```
┌──────┬──────────────────────────────────────────────┬──────────────────┬─────────┬─────────────────────────────────────────┬─────────┐
│ PH   │ deliverable                                  │ repo / file      │ app be- │ gate                                    │ needs   │
│      │                                              │                  │ haviour │                                         │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ ✅V1 │ frame-identity — ⭐ ANSWERED FROM THE ARCHIVE  │  —               │  none   │ 82 % distinct · W=50 ≙ 41 · margin 4.0σ │  DONE   │
│      │ ⚠ re-confirm at frameCount 60, next rig day  │                  │         │ (rides any rig session; blocks nothing) │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P1a  │ ⭐ THE SDK TIER (P1 = P1a+P1b)                │ -core            │  none   │ ⭐ fake evaluator + SYNTHETIC TIMESTAMPS │    —    │
│      │ FrameRing · MonitorEngine · BurstEvaluator · │ plugin_sdk/      │         │ (X6): a 90-min curve replays in ms;     │         │
│      │ Row · Decision · Result · Policy   (I3)      │  acquisition/    │         │ ⭐ decision rows keyed on FRAME index    │         │
│      │ ⭐ monotonic clock (X3) · single-use (X4)     │                  │         │ (X2); ⛔ engine names no wavelength      │         │
│ P1b  │ ⛔ export the parts in __init__ + __all__ (M1)│ -core            │  none   │ an sdk-only source passes the lint      │  P1a    │
├──────┼──────────────────────────────────────────────┼──────────────────┼─────────┼─────────────────────────────────────────┼─────────┤
│ P2a  │ ⭐ THE PLUGIN TIER (P2 = P2a+P2b)             │ -plugins         │  none   │ ⛔ exactly ONE definition of the metric; │  P1b    │
│      │ monitorMetrics() PUBLIC; __vTerms delegates  │ DevSpectralPlugin│         │ ⛔ box_metrics.py NOT repointed (X7)     │         │
│ P2b  │ class ClearingEvaluator (TEST A + TEST B, j, │ -plugins         │  none   │ ⭐⭐ decide() replayed on the 2026-08-14  │  P2a    │
│      │ latch, branches, coach) + createMonitor      │ ⛔ SAME FILE (M1)│         │ CSV rows → t ≈ 16.7, reads 13.27;       │         │
│      │ ⚠ numerical guards carried over (X8)         │                  │         │ ⚠ raises are FAILED + partial kept (X5) │         │
├──────┼──────────────────────────────────────────────┼──────────────────┼─────────┼─────────────────────────────────────────┼─────────┤
│ P3   │ SCRIPT on the plugin; DIAGNOSTIC mode;       │ spectracsPy      │ ⚠ diag  │ ⭐ CSV+npz flushed from `finally:` — on  │  P2b    │
│      │ appFrameSpectrum (M2); clearingSeconds from  │ diagnostics/     │  only   │ Ctrl-C AND on a raise; ⛔ npz written    │         │
│      │ the first frame (V4); ⛔ npz = RAM + write    │                  │         │ ONCE, not appended (X1)                 │         │
│      │ once (X1)                                    │                  │         │                                         │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P4   │ ⭐⭐ §11 THE HEAT-DOSE EXPERIMENT              │ ⛔ NO CODE — rig │    —    │ 4 arms × 20 min, identical arcs,        │  P3     │
│      │                                              │                  │         │ pre-warmed; §11.5's rule applied as-is  │         │
├══════┼══════════════════════════════════════════════┼══════════════════┼═════════┼═════════════════════════════════════════┼═════════┤
│ P0   │ ⭐ Cancel + hard caps on TODAY's burst        │ spectracsPy      │  ⚠ YES  │ ⭐ the MEASURE BUTTON relabels (§12.1a): │ ⭐ none  │
│      │ (INDEPENDENT — blocks nothing)                │ engine + panel   │         │ stays ENABLED while busy; guidance cue  │         │
│      │                                              │                  │         │ suppressed; cancel works during AE too  │         │
│ P5   │ ⛔ UNIFY: captureAcquisitionStep delegates;    │ spectracsPy      │ ⛔ THE  │ ⭐⭐ BOTH existing burst tests pass       │P1a,P0   │
│      │ C3 as nAccepted ≥ N (I4); ⛔ no flag (M5)      │ engine           │ ONE step│ UNCHANGED, incl. the dim-frame fixture  │         │
│ P6   │ HOST: captureMonitoredStep · legend box ·     │ spectracsPy      │  ⚠ YES  │ click-through; ⛔ I1 fixed (ONE frame);  │ P5, P4  │
│      │ indeterminate bar · U2/U3 · ⚠ plot from a    │ panel + views    │         │ ref re-capture discards the monitor     │         │
│      │ TIMER, not the row callback (V3)             │                  │         │ (X4/I6); nAccepted dip ≠ a fault (V2)   │         │
│ P7   │ PERSISTENCE: generic MonitorRecord + ⭐ the   │ spectracsPy      │  ⚠ YES  │ saved run re-opens and redraws; rows a  │  P6     │
│      │ effective-distinct fraction (V1)             │ (+ -model if any)│         │ LIST; ⚠ expect NO migration             │         │
│ P8   │ SeriesPlotView (per-panel log) + Settling    │ -core/-model,    │  ⚠ YES  │ ⭐ ONE view, three uses; tabs FLATTEN    │  P7     │
│      │ step [Overview|Health] + PDF flattening      │ -plugins, Py     │         │ to PDF sections                         │         │
│ P9   │ ⚠ OPTIONAL, LAST: TableView + [Decisions]     │ -core, Py        │  ⚠ YES  │ renders any plugin's record blind       │  P8     │
└──────┴──────────────────────────────────────────────┴──────────────────┴─────────┴─────────────────────────────────────────┴─────────┘

  ⭐ P1 = P1a+P1b (the SDK tier) · P2 = P2a+P2b (the plugin tier). There is no bare P1 or P2.
  ⭐⭐ P1a..P2b change NOTHING that runs today; the path to the experiment
      (P1a → P1b → P2a → P2b → P3 → P4) touches the shipped app in ⭐ no place at all.
  ⭐ P0 is independent and can be done at any time — it is also the smallest way to get §12.1a in front
     of a user and find out whether one relabelling button reads as clearly as it sounds.
  ⛔ P6 must not start before P4.
```

---

## ⭐⭐ 27 · AS-BUILT — what was implemented on 2026-08-17, and what deliberately was not

```
┌──────┬──────────────────────────────────────────────┬─────────┬────────────────────────────────────────┐
│ PH   │ deliverable                                  │ state   │ evidence                               │
├──────┼──────────────────────────────────────────────┼─────────┼────────────────────────────────────────┤
│ P1a  │ FrameRing · MonitorEngine · BurstEvaluator · │ ✅ DONE │ tests/test_monitor_engine.py (10)      │
│      │ MonitorRow/Decision/Result/Policy/Outcome/   │         │ ⭐ a FAKE evaluator drives it, so the   │
│      │ Mode, in spectracsPy-core/plugin_sdk/        │         │ engine provably names no wavelength    │
│      │ acquisition/                                 │         │                                        │
│ P1b  │ exports in plugin_sdk/__init__ + __all__     │ ✅ DONE │ the plugin imports them and loads      │
│ P2a  │ public monitorMetrics(); __vTerms is now the │ ✅ DONE │ one definition of the metric; the      │
│      │ internal tuple face of the SAME computation  │         │ 365-test suite unchanged               │
│ P2b  │ ClearingEvaluator + createMonitor(), in the  │ ✅ DONE │ tests/test_clearing_evaluator.py (7)   │
│      │ plugin's OWN file (§21/M1)                   │         │ ⭐ replayed on the REAL 2026-08-14 CSV  │
│ P3   │ diagnostics/settling_run.py — the script ON  │ ✅ DONE │ imports + drives the real plugin       │
│      │ the plugin, --npz, DIAGNOSTIC mode, Ctrl-C   │         │ headlessly; ⚠ NOT yet rig-run          │
│      │ flush, app-tier frame extraction             │         │                                        │
│ P0   │ cancel (⭐ the Measure button relabels) +     │ ✅ DONE │ ⭐ CLICK-THROUGH PASSED 2026-08-17      │
│      │ the I1 memory fix + guidance-cue suppression │         │                                        │
│ P5   │ captureMonitoredStep() as a SIBLING method   │ 🟡 PART │ both burst tests pass UNCHANGED        │
│ P6   │ host wiring: monitored capture · striped bar │ ✅ DONE │ ⭐ CLICK-THROUGH PASSED — a real fill   │
│      │ from the click · Settling tab under Sample   │         │ measured end to end                    │
│ P7   │ MonitorRecord on the workflow + migration    │ ✅ DONE │ `84fe759ba6d7`, one nullable column    │
│ P8   │ SeriesPlotView, BOTH renderers, the summary  │ ✅ DONE │ text Overview + one tab per curve;     │
│      │ ⭐ attached to the SAMPLE step (§27.12)       │         │ ⚠ that move awaits a click-through     │
│ P9   │ TableView + the [Decisions] sub-tab          │ ✅ DONE │ renders any plugin's record blind      │
├──────┼──────────────────────────────────────────────┼─────────┼────────────────────────────────────────┤
│ P4   │ ⭐⭐ THE HEAT-DOSE EXPERIMENT                  │ ⛔ RIG   │ Edwin's to run — no code involved      │
└──────┴──────────────────────────────────────────────┴─────────┴────────────────────────────────────────┘
```

### ⚠ 27.1 THE TWO DELIBERATE STOPS

⛔ **P5 was NOT completed as "the engine delegates to the monitor".** `captureMonitoredStep()` was added
**beside** `__runBurst`, not in place of it. ⭐ The reason is that the benefit §12.1 claimed for the
unification — *"cancel is implemented once and every plugin gets it"* — **was delivered without it**: the
panel's provider returns `None` on the cancel flag, and `__runBurst`'s existing `maxAttempts` bound is
what unwinds it. ⇒ replacing a proven reduction path bought nothing that was not already in hand, and
`test_frame_provider_burst` / `test_capture_frame_rejection` would have been the only thing standing
between a subtle change and the archive. ⚠ The unification remains available and its gate is unchanged.

⛔ **P6/P7/P9 were not started, and §26 is the reason:** *"P6 must not start before P4 — a coach line
tuned against a read rule the experiment may still change is work done twice."* ⭐ §11's experiment can
change the read rule; it cannot change the SDK parts, the evaluator or the script, which is exactly why
those were built first. ⚠ What P8 contributed meanwhile is the half that does NOT depend on the outcome:
the view MODEL and the plugin's own `settlingStep()`. Its two renderers (screen + matplotlib) wait.

### ⭐ 27.2 WHAT THE IMPLEMENTATION CHANGED IN THE SPEC — three corrections, all from the real data

| | |
|---|---|
| ⛔ §14.3 rule 3 | "j = 2 windows" ⇒ ⭐ **a span in SECONDS**. Replayed on the archive's 3.28-minute samples, a window count doubles a span that was already right and the gate fires two samples late |
| ⛔ §14.2 the vertex | read around the **Q% minimum**, ⛔ not around the gate row. On the real curve they are 3.3 minutes apart, and fitting around the gate fits a rising ramp whose parabola has no minimum at all |
| ⭐ the promoted SPECTRUM | must be the **minimum row's**, which is two decision rows behind the confirmation — so `MonitorDecision` carries `promoteRow`, and the engine keeps the last few rows' spectra alive (and only those) |

⇒ ⭐⭐ **Every one of those was invisible in prose and obvious against the measured curve.** The spec was
right that P2b's acceptance gate is the replay; it was the replay that found them.

### ⭐⭐ 27.4 P6 / P7 / P9 — IMPLEMENTED 2026-08-17 on Edwin's instruction, ahead of P4

> ⚠ §26 ordered these AFTER the rig experiment. ⭐ Edwin overrode that deliberately; the ordering risk it
> was protecting against is unchanged and stated here so it is not forgotten: **§11 can still move the
> read rule, and anything tuned against today's rule may need re-tuning once.** What it CANNOT move is
> the shape of the views or the record — which is why these three landed cleanly anyway.

| | delivered |
|---|---|
| **P6** | `CapturePanel.__monitorFor()` asks the PLUGIN for a monitor (SAMPLE only, and only once a reference exists) · `captureMonitoredStep` drives it · ⭐ the **legend box** inside the step (`__coachLabel`) · ⛔ **indeterminate** status bar via `stepsCount = 0` · per-row paint throttled to ~2 s (§23/V3) · every outcome says WHY, incl. §17/U2's "use a fresh fill" |
| **P7** | `SpectralWorkflow.monitorRecordJson` + `get/setMonitorRecord()` · ⭐ Alembic migration `84fe759ba6d7` (ONE nullable TEXT column) · written at the end of a successful monitored capture |
| **P8/P9** | `SeriesPlotView` + `TableView` view-models · **both** render targets (`QtWorkflowRenderer`, `MatplotlibWorkflowRenderer`) · the visitor ladder extended once, so screen and paper cannot drift · the plugin's `settlingStep()` with ⭐ sub-tabs **Overview / Health / Decisions**, each conditionally present |

#### ⛔ 27.4a A PREDICTION THAT WAS WRONG — §19/I7's "expect NO migration"

§19/I7 said the record would ride the workflow's JSON blob, so no schema change was expected. ⛔ It does
not: `SpectralWorkflow` is **Option A** — the workflow IS the row, with real columns and relationships,
and `toReportJson()` is a *serialiser*, not storage. ⇒ a nullable `Text` column and a migration were
required after all. ⭐ The flag "⚠ Verify before assuming" is what stopped that from becoming a surprise.
⚠ **The dev DB needed `alembic upgrade head` before the persistence tests would pass** — which is what
`DatabaseInitializer` does at app boot, so no user action is implied.

#### ⭐ 27.4b THE SUB-TAB RULES, AS BUILT

⭐ **Overview is always first and always answers alone** — `Q%` and `A_valley` on one screen, because
judging an answer means seeing where the gate fired relative to the trace (§18.8).
⭐ **Health appears only when it has something to say** (nAccepted dipped, or `A_Soret` ran near the
floor), and its caption states that ⚠ **a dip while the fill clears is EXPECTED, not a fault** (§23/V2).
⭐ **Decisions appears only on runs long enough to need it** (< 8 decision rows and the plots already say
everything). ⇒ a two-minute product run yields exactly one tab, and a miller's PDF never carries a page
of empty diagnostics.

### ⭐⭐ 27.5 FIRST RIG CLICK-THROUGH, 2026-08-17 — two findings, and one was a spec violation

Edwin ran the bench against an old, muddy oil. The gate behaved correctly (`A_valley` 0.9 falling
0.0388/min → 0.0614 falling 0.0013/min, i.e. under θ). ⚠ Two things were wrong around it.

#### ⭐ 27.5a THE SPECTRUM WAS NOT PAINTED DURING SETTLING  *(Edwin: "it should be painted to see some progress anyway")*

⛔ The burst path always painted per frame (`onFrame` → `__plotRoleSpectrum`); the monitored path painted
only text. ⇒ for twenty minutes the plot sat empty and **the instrument looked dead** — exactly backwards,
since the longer run is the one that needs to show life.
⭐ Fixed: the row's WINDOW MEAN is plotted on the same ~2 s throttle as the coach line — the same
spectrum the row's numbers came from, so what the operator watches and what the gate reads are one
object. ⚠ On the throttle, not per row: §23/V3's `event.set()` handshake means a per-row redraw would
throttle the very stream being measured.

#### ⛔⛔ 27.5b THE SETTLING STEP DID NOT APPEAR — and the cause was a rule I wrote and then broke

⛔ **The record was only written when the run produced a VALUE.** §12.1 says the opposite in as many
words: *"the trajectory so far is KEPT, marked, and never reported as a measurement."* ⇒ every run worth
diagnosing — never settled, cancelled, broken — threw its curve away.

⛔ **And a second, compounding fault:** the settling step was built at the END of `processing()`. A run
with no value leaves the SAMPLE step deliberately uncaptured (§12.1), so `TransmissionOp` raised on the
missing container and the whole phase died — ⭐ **killing the one tab that could explain why, in exactly
the runs that need explaining.**

```
   ⭐ the record is now written for EVERY outcome
   ⭐ the settling step is declared FIRST, before any measurement maths
   ⭐ processing() returns cleanly with ONLY that tab when a role is uncaptured
   ⭐ + a greppable MONITOR outcome=… line per run, beside CAPTURE-SETTINGS / CAPTURE-LOWDN
```

⇒ ⭐⭐ **THE RULE THIS ESTABLISHES: a diagnostic must survive the failure of the measurement it
documents.** Regression test: `tests/test_settling_step_endtoend.py` drives a NEVER_SETTLED run through
`processing()` and asserts the tab is there.
⚠ It is also the answer to a question §18 never asked: what a Settling tab looks like when there is no
answer to head it. Now: the outcome, and the curve that failed to flatten.

### ⭐⭐ 27.6 SECOND RIG CLICK-THROUGH — the run was RIGHT, the presentation was not  *(2026-08-17)*

⭐⭐ **The measurement itself validated the whole design**: `SETTLED_IMMEDIATE · arrived-clear · read as
FIRST_SETTLED_WINDOW · Q% 17.19 at 1.68 min · ✓ in domain · distinct frames 87.9 %`. ⇒ §9.6's
arrived-clear branch fired on a real fill, §14.2a's "~2 minutes" was accurate, and §23/V1's 82 % duplicate
figure reproduced at 87.9 % on live hardware at frameCount 60. ⚠ Four presentation faults around it.

#### ⛔⛔ 27.6a A CATEGORY ERROR IN THE PLOT — θ IS A RATE, THE AXIS WAS AN ABSORBANCE

The gate threshold was drawn as a horizontal level at **y = 0.0017 on the `A_valley` panel**. ⛔ θ is
`0.0017 **per minute**`; that axis is absorbance. The line asserts an equivalence that does not exist —
and it dragged the axis range down past the data, which is what made the panel unreadable.
⇒ ⭐ **the criterion gets its OWN panel**, `|Δ A_valley / Δt|` against θ, in its own units, where
convergence is what the eye actually follows. ⭐ Its rates come from `ClearingEvaluator.rateAt()` — the
SAME method the gate decides with — because ⛔ a diagnostic that computes its own version of the number
it is diagnosing is a diagnostic that can lie.

#### ⛔ 27.6b LOG SCALE ON A FLAT SERIES IS WORSE THAN LINEAR

§18.7 said the gate panel "wants log" — true for a CLEARING curve falling 40×, ⛔ false for an
arrived-clear fill sitting at 0.0265, where pyqtgraph's decade minor ticks (0.01 · 0.02 · 0.03 · 0.04 ·
0.06 …) smear into an unreadable column beside a line that never moves.
⇒ ⭐ **log only when the data actually spans a decade**, decided per panel from the data itself.

#### ⚠ 27.6c THE SUB-TABS WERE THERE — the conditions were simply too strict

Only "Overview" appeared, so the feature looked missing. It was working as specified: Health was
withheld (nothing dipped) and Decisions needed **8** rows while a settled 1.7-minute run has ~3.
⇒ ⭐ Decisions now needs **2** — on the MASTER bench three rows of "here is exactly what the gate
compared" is the point. ⚠ Health stays conditional; that one is the whole idea.

#### ⛔ 27.6d THE INDETERMINATE BAR NEVER WORKED — IT WAS RAISING

`MainStatusBarViewModule` computed `currentStepIndex / float(stepsCount)`, so §13.2's `stepsCount = 0`
convention hit a **ZeroDivisionError inside the signal handler** every 2 s and left only the text.
⇒ ⭐ `stepsCount` falsy now sets Qt's busy range `(0, 0)` — the chunk ANIMATES instead of filling, which
is the honest "something is happening, the end is not knowable" signal — and `resetProgressBar()`
restores `(0, 100)` so it cannot animate forever.

#### ⭐ 27.6e THE SETTLING TAB MOVED TO THE **SAMPLE** STEP  *(Edwin: "it should be in the 'Sample' pseudo-setup")*

It first landed in PROCESSING beside the other provenance views. ⚠ But the operator reads it **while and
just after measuring this jar**, and that is the Sample step. ⇒ it is now a third inner tab there, beside
Spectrum and Image, shown for EVERY outcome including the ones with no value.
⚠ **The PROCESSING declaration stays** — it is the persisted, re-openable artefact and the page that
reaches the PDF. Same view-model, two surfaces: §18.1's "built once, used three times" earning its keep.

### ⭐ 27.7 THIRD RIG CLICK-THROUGH — a live run, and two finishing faults  *(2026-08-17)*

⭐ The mid-run screenshot shows the fixes landing: the **spectrum is painted** (camera-DN axis, the DN
guard line visible), the button reads **Cancel**, and the legend box carries `clearing … turbidity
0.0719`. ⚠ Two things around it.

#### ⛔ 27.7a THE AMBER CUE WAS STILL ON THE "CANCEL" BUTTON

§12.1a's suppression was added to `AcquisitionGuidance.paint...`, ⛔ but the BENCH paints dots through
its own `__setButtonDot` path — so one of the two hosts still urged the operator, with an amber dot, to
press the control that **abandons the measurement**.
⇒ ⭐ the guard moved DOWN into `setButtonDot()` itself, where every caller passes: a button whose text
starts with "Cancel" never receives the cue. ⚠ Fixing it at the call sites is what let it survive once.

#### ⭐⭐ 27.7b "MOVING STRIPES", AND QT'S OWN BUSY MODE WAS THE WRONG TOOL  *(Edwin: "would like 'moving stripes' … as known by other apps")*

Qt's indeterminate mode (range 0,0) slides ONE chunk — and ⛔ **swallows the format text**, which is the
half of §13.2 that carries the state and the turbidity. The screenshot shows exactly that: motion, no
words.
⇒ ⭐ the bar is kept **full** and its chunk painted with a striped gradient whose phase a **70 ms timer**
advances (~14 fps — cheap beside a 1.4 fps camera). ⚠ Qt stylesheets have no animation, so re-applying
the sheet IS the mechanism, not a workaround.
⚠ Three exits are wired, because an animation that outlives its cause reads as "still working": a
determinate signal, a status reset, and a guidance line each stop the timer. ⭐ And guidance text is
explicitly excluded — it also carries `stepsCount = 0` and must stay a plain amber line.
Regression: `tests/test_status_bar_indeterminate.py` (5 tests, including "the text survives").

### ⭐ 27.8 ONE TAB PER GRAPH — added BESIDE the combined view, not instead of it  *(Edwin, 2026-08-17)*

⭐ Three stacked panels in a fixed-height step leave each of them short, and **one curve read closely is
a different job from three read together**. ⇒ the tab bar becomes:

```
   [ Overview ] [ Q% ] [ Turbidity ] [ Rate ] [ Health ] [ Decisions ]
     combined     ⭐ the same panel objects, one per tab, at full height
```

⚠ **§18.8'S RULE IS UNCHANGED AND IS WHY OVERVIEW STAYS FIRST AND STAYS COMBINED.** Judging an answer
means seeing **where the gate fired relative to the `Q%` trace**; a per-graph tab cannot show that, and
⛔ it must never become the only place a curve can be seen. The single-graph tabs are for looking
*closer*, which is a genuinely different question from the one Overview answers.

⛔ ~~**`shownInReport` is FALSE on them**, and that is not an oversight: tabs FLATTEN to sections on paper
(§18.8), so marking all four would print the same three curves twice — once combined, once one per page.~~
⭐ This is the first real use of the per-tab report flag that §18.8 asked for.
⛔⛔ **REVERSED IN §27.21 — AND THE REASON ABOVE HAD ALREADY EXPIRED WHEN IT WAS WRITTEN DOWN.** "Twice"
was only possible while Overview was the COMBINED chart. §27.9 (three paragraphs below) turned Overview
into a TEXT summary with no chart, which deleted the duplication — but nobody came back for the flags.
⚠ Each per-graph tab holds **the same panel dict** the Overview holds — one construction, two homes. A
copy would be two things to keep in step, and they would drift.

### ⭐⭐ 27.9 THE PRESENTATION, SETTLED — three of Edwin's calls, two of which REVERSE this spec  *(2026-08-17)*

⚠ Recorded as reversals rather than quietly rewritten, because both rules were argued for here at length
and Edwin overruled them **after seeing the built thing**, which is the better evidence.

| | |
|---|---|
| ⛔ **Overview carries NO chart** — it is a TEXT summary | REVERSES §18.8's "the first tab must answer alone, with `Q%` and `A_valley` on one screen". Three stacked panels in a fixed-height step left every one of them short, and the things that answer *"what did I measure and can I trust it"* are **numbers**: outcome · `Q%` · verdict domain · read-as · read-at · clearing time · decision rows · frames accepted · policy · evaluator · distinct frames. ⚠ The cost is real and stays stated: correlating the gate with the `Q%` trace now takes two tabs |
| ⛔ **No Settling step in PROCESSING** | it lives ONLY as an inner tab of the SAMPLE capture step, where the operator reads it. ⚠ **Consequence, asserted in a test so it cannot be forgotten: the settling summary and curves NO LONGER REACH THE PDF** — the report is assembled from the workflow's flagged views. ⭐ The record itself still persists (§15.2), so nothing is lost; §18's "it also enters the PDF" is simply not true today |
| ⛔ **No legend box under the spectrum** | REVERSES §13.2's placement (also Edwin's, earlier). During a run the state belongs in ONE place — the status bar, which is already animating for exactly that purpose. A second copy competed with the curve and stole height from the one thing showing progress |

⭐ **What the Overview gained by becoming text:** it renders through the ordinary metric grid, so it
lines up exactly like the EVALUATION rows the operator already reads, every row carries a tooltip
explaining *why* that number matters, and a run with **no value** now says `— none —` with the reason,
instead of being an empty chart.

⭐ **One small generalisation fell out of it:** `TabGroupView.addTab()` now accepts a **list** of
view-models as well as one, and both renderers dispatch the list. A summary tab is a heading plus a
column of rows — several view-models — and forcing that into one would have meant inventing a "summary
view" that the metric grid already renders.

### ⭐ 27.10 THE BAR STARTS AT THE CLICK  *(Edwin, 2026-08-17)*

⛔ It used to start at the FIRST ROW. Between pressing Measure and that row sit the ~15 s auto-exposure
sweep **and** a whole window of frames (~43 s at W = 60) — ⚠ **about a minute in which the app showed
nothing and looked as though it had ignored the click.**

```
   click            -> ⭐ striped, "Measuring sample …"        (nothing about the duration is knowable yet)
   AE sweep         -> ⭐ striped, "Auto-exposure sweep …"     (~15 s that used to be silent)
   monitored rows   ->    striped, "clearing …  turbidity 0.0719  -0.0042/min"
   OR a plain burst ->    determinate, "Capturing sample frame 34 / 60"   ⭐ swaps itself in
   finished         ->    reset, "ready for action..."
```

⭐ Indeterminate **from the outset** is the honest state: at the moment of the click the host does not
yet know whether the plugin will even return a monitor, let alone how long the fill will take. The burst
path swaps in its real fraction on its first frame; the monitored path keeps animating and swaps in the
coach text.

### ⭐⭐ 27.11 → 27.12 · WHERE THE SETTLING VIEWS BELONG — two wrong answers, then the right one  *(2026-08-17)*

⚠ Kept as the sequence it actually was, because each wrong answer was wrong for an instructive reason.

#### ⛔ ATTEMPT 1 — a rendered WIDGET in a tab bar

`CapturePanel.__showSettlingTab()` built the views from the record and dropped the resulting **QWidget**
into its inner tab bar. ⇒ it reached nothing: **the report collects VIEW-MODELS, never widgets**, and
those view-models were attached to no step at all.

⛔ **And the explanation first written here was wrong**: it said "anything that must reach the paper must
be a step, and Sample is not one". ⚠ **Sample IS a real workflow step** — measured, not assumed:

```
   step Reference  role=REFERENCE  view=CaptureView  -> report sees [Capture, Capture, SpectrumPlot]
   step Sample     role=SAMPLE     view=CaptureView  -> report sees [Capture, Capture, SpectrumPlot]
```

⇒ the report was **already harvesting that step's `EvaluationResult`**. The settling views simply were
not in it.

#### ⛔ ATTEMPT 2 — a report-only STEP in PROCESSING, with a persisted flag

A second step, declared in PROCESSING so the report would find it, plus `SpectralWorkflowStep.reportOnly`
and a `renderStep()` guard so no host drew it. It worked. ⛔ **And it was the wrong shape, with a tell:**
the same record was now built **twice** — once by `processing()` for the report, once by the panel for
the tab — into two homes, with a persisted column invented to hide one of them.
⚠ *A flag whose job is to hide something is usually a sign the something is in the wrong place.*

#### ⭐⭐ THE PROPER FIX — the views hang off the step they DESCRIBE

The settling curves are provenance of ONE capture. So they go on that capture's step:

```
   captureMonitoredStep(...)                          # already sets step.container from the result
       view = plugin.settlingView(result.toRecord())  # ⭐ ONE construction
       step.getEvaluationResult().addItem(view)       #   ...one home
       result.views = [view]                          #   ...and the panel renders these very objects
```

| | |
|---|---|
| the report | harvests that step's `EvaluationResult` **already** — no new mechanism at all |
| the section | ⭐ files under **Acquisition**, where the measurement happened, not under Processing |
| the panel | renders the *declared* objects instead of inventing a widget — the host stops building views the plugin owns |
| persistence | rides along: `EvaluationResult` items round-trip through `ViewModelFactory`, where both new view types are registered |
| invisibility | ⭐ **by construction, not by flag**: `renderStep()` sends a CaptureView step to the capture path, which never looks at the `EvaluationResult`. Nothing to remember, nothing to forget |
| ⛔ `reportOnly` | **removed**, and dropped by migration `dccf62fc4d10`. It solved a problem created by putting the views on the wrong step |

⚠ Re-measuring a role **replaces** the attached view rather than appending: two curves on one capture
would be two contradictory provenances for one number.
⭐ And `toReportJson()` carries `monitorRecord`, so **both halves** of the PDF — the visible section and
the embedded machine payload — describe how the value was chosen. §18.6's claim is now actually true.

#### ⚠ A SILENTLY VACUOUS TEST, FOUND ON THE WAY

`step.getRole() == "sample"` matched nothing — the role is `"SAMPLE"` — so a test that claimed to check
"a valueless run does not take PROCESSING down" had been asserting against an untouched workflow. ⇒ the
role CONSTANTS are used now. ⛔ A test that cannot fail is worse than no test: it reports safety it never
checked.

### ⭐⭐ 27.13 THE REPORT PATH, WALKED END TO END — three defects, measured not guessed  *(Edwin's review of §27.12, 2026-08-17)*

⚠ **WHY THIS SECTION EXISTS.** Edwin, on reading §27.12: *"have a bad feeling about it and still don't
understand it."* ⛔ That is a legitimate objection to a design, not a request for reassurance — §27.12 was
written from the code that was changed, never from the artefact it produces. ⇒ the chain was walked
object by object, and the report renderer was **run** on a synthetic 12-row `MonitorRecord`. Two of the
three findings below were invisible from the diff and only appeared on the rendered page.

#### ⭐ 27.13a THE CHAIN, AS BUILT — five hops, one object

| # | where | what happens |
|---|---|---|
| 1 | `DevSpectralPlugin.settlingView(record)` | builds **one `TabGroupView`**, `setShownInReport(True)`: `Overview` (a LIST — `LabelView` + ~11 `MetricFieldView`), `Q%`, `Turbidity`, `Rate` (a `SeriesPlotView` each), `Health`, `Decisions` (a `TableView` each, conditional) |
| 2 | `SpectralWorkflowEngine.__attachMonitorViews` | appends it to the **monitored step's** `EvaluationResult`, tags `isMonitorView = True`, and returns the SAME object on `result.views` |
| 3 | `CapturePanel.__showSettlingTab` | renders `result.views` through `QtWorkflowRenderer` into the "Settling" inner tab |
| 4 | `WorkflowReportBuilder.__collectGroups` | harvests each step's `EvaluationResult` items, keeps `isShownInReport` ⇒ the group files under **Acquisition** (its step's PHASE — no role, label or step-kind is consulted anywhere) |
| 5 | `MatplotlibWorkflowRenderer.visitTabGroup` | "paper has no tabs" — stacks the children under their tab labels as bold headings |

⭐ **HOW THE ENGINE CALLS THE PLUGIN — duck-typing, not an SDK method.**
`plugin = getattr(self, "plugin", None)`, then `hasattr(plugin, "settlingView")`, then
`plugin.settlingView(result.toRecord())` inside a `try`. ⚠ `settlingView` is **not** declared on
`SpectralPlugin`: a plugin without it simply gets no views, and a plugin whose implementation raises gets
a printed line and a capture that still succeeds — *a diagnostic must never break the capture it
documents*. ⛔ The cost of that freedom is that a typo in the method name is silent, which is exactly the
failure mode of the vacuous-test paragraph above. ⇒ **when the seam is next touched, declare it on the
SDK base class with a `return None` default** and keep the try.

⭐ **"SAMPLE" IS NEVER MATCHED BY NAME.** Nothing in the engine or the report keys on a role. The only
role gate is in the UI: `CapturePanel.__monitorFor` refuses `REFERENCE` and refuses to build a monitor
before a reference exists. ⇒ the phrase "hard-coded by its label" belongs to two *removed* things — the
report-only step of §27.11, and the `== "sample"` literal in the test.

#### ⛔⛔ 27.13b DEFECT 1 — `isShownInReport` IS IGNORED INSIDE A TAB GROUP, so the PDF prints EVERYTHING

`visitTabGroup` dispatches every child unconditionally; the flag is consulted **only on top-level items**
in `__collectGroups`. ⇒ the plugin's own contract (`DevSpectralPlugin` §18.8: *"shownInReport stays FALSE
on them … the report takes the summary, not three separate pages"*) is **not what the code does**.

⭐ **MEASURED, on a 12-row record: three pages.** Page 0 = the Overview metric grid + the Q% plot + the
top of Turbidity; page 1 = Turbidity, Rate and the Health table; page 2 = the whole Decisions table.

⚠ **WHY IT SURVIVED.** `test_one_tab_per_graph_each_holding_exactly_one_panel` asserts the flag's
**value**, never its **effect** — the third time in this spec that a test has checked a declaration
instead of a consequence (§27.5b, the vacuous role literal, now this). ⛔ And the one existing
`visitTabGroup` report test (`test_tab_group_render.py`) only asserts *"figures is truthy"*, which a page
carrying nothing but a header also satisfies.

⚠ **WHY NOTHING ELSE BROKE.** The only other `TabGroupView` is the PROCESSING raster group (Full frame |
Cropped ROI) — and it is **not** `shownInReport` at all, so it never reaches the report. ⇒ the settling
group is the FIRST and ONLY tab group that has ever been printed, and the first with deliberately mixed
children. The renderer's comment (*"e.g. full-frame + cropped-ROI raster"*) documents a case that does
not happen.

⭐⭐ **DECISION D1 (Edwin): `isShownInReport` IS THE CANONICAL WAY TO SAY WHAT IS ON PAPER, AND A TAB GROUP
MUST HONOUR IT.** `visitTabGroup` prints a child only when that child is flagged; a tab whose children
are all unflagged prints no heading either (⛔ never an empty bold label). ⚠ Consequences, both of which
are the work of this change and neither of which is optional:
- **the `Overview` tab's items must be flagged by the plugin** — they are a `LabelView` + `MetricFieldView`
  list, all defaulting to `False`, so under D1 the summary would silently vanish. ⛔ That failure is
  invisible in every current test.
- **`test_tab_group_render.py`'s report assertion must be strengthened** from "figures is truthy" to a
  count of what was actually drawn (axes / texts), or D1 lands unverified.
⛔ **Rejected: inheritance** ("an unset child inherits the group's flag"). A class-attribute default
cannot distinguish *unset* from *explicitly False*, so it would have to peek into `__dict__` — clever,
and it would make the plugin's explicit `False` on the graph tabs mean nothing.

#### ⛔ 27.13c DEFECT 2 — `isMonitorView` DOES NOT SURVIVE A SAVE

The de-duplication tag is a bare Python attribute assigned by the engine; `TabGroupView.toJson()` does
not carry it. **Measured**: after a JSON round-trip the reloaded group has `isShownInReport = True` and
`isMonitorView` **absent**. ⇒ re-measuring inside a reloaded run appends a SECOND settling group instead
of replacing the first, and the PDF then carries two contradictory provenances for one number — precisely
the failure the tag was introduced to prevent (§27.12).

⭐ **DECISION D2:** the tag round-trips. It is written and read in `TabGroupView.toJson()/fromJson()`
alongside `isShownInReport`, and the *contract* is stated on the SDK seam: **whatever `settlingView()`
returns must round-trip `isMonitorView`.** ⚠ Today that is only `TabGroupView`; a plugin returning another
type gets the dedup silently downgraded, so the engine logs one line when the returned view cannot carry
the tag.

#### ✅ 27.13d REOPENING A SAVED RUN — it already works, by accident, and untested

*Edwin: "at opening a workflow the GUI should show/render the settlement values of course."* ⭐ It does —
**measured** end to end (JSON round-trip → `renderStep`): all six tabs come back with their child types
intact (`SeriesPlotView`, `TableView`, the `MetricFieldView` list) and `renderStep` yields a `QTabWidget`
reading `Overview · Q% · Turbidity · Rate · Health · Decisions`.

⚠ **BUT IT WORKS FOR A REASON NOBODY CHOSE.** `SpectralWorkflowStep._view` is `@reconstructor`-transient,
so a step loaded from the DB has **no `CaptureView`** — `renderStep` therefore falls past the capture
branch into the passive visitor, which reads the `EvaluationResult`. ⇒ the very mechanism that makes the
settling views *invisible* during a live run (§27.12's "invisible by construction") is what makes them
*visible* in a saved one. That symmetry is elegant, and it is currently written down nowhere and asserted
by no test.

⭐ **DECISION D3:** promote it from accident to contract. One test opens a persisted monitored run and
asserts the settling tabs are present; the `_view`-transience argument is written into
`WorkflowPhaseRenderer.renderStep`'s comment, because a future "persist the view descriptor" change would
silently take the saved-run settling tabs away.

⚠ **AND A SCOPE FACT WORTH KNOWING:** saved runs open **only in the wizard** (`WizardViewModule.__startRun`
→ `_startViewRun`; the bench has no VIEW mode and its `_renderStop` builds a live `CapturePanel`
unconditionally). ⛔ So a monitored run made at the bench is re-read in the *wizard*. That is not wrong,
but it means the bench — the host that MAKES these runs — cannot re-open one. Recorded here; a bench VIEW
mode is out of scope for §27.

#### ⚠ 27.13e A COSMETIC ONE — the paper section is headed "Overview"

The tab label becomes the bold heading, so the PDF reads **Overview** with no "Settling" above it; the
word appears only inside the `LabelView` beneath. ⭐ Fix with the group: a `TabGroupView` that is
`shownInReport` prints its own **title** as the section heading, above the per-tab labels.

#### ⭐ 27.13f "SAMPLE LOOKS LIKE A PHASE" — that is the CHEVRON, not the tab groups

*Edwin: "mechanism that shows Sample as if it were a phase though it in fact belongs to the ACQUISITION
phase."* ⛔ Nothing to do with `TabGroupView`. It is `NavigationModel.stops()`: when the plugin's
`NavigationPolicy` lists a phase in `stepChevronPhases`, that phase contributes **one `NavStop` per step**
instead of one per phase, labelled with the STEP's label. `DevSpectralPlugin.policy()` sets
`stepChevronPhases={ACQUISITION}` (with `AUTO_ADVANCE`) ⇒ the chevron reads
`Reference › Sample › Processing › Evaluation › …` and "Sample" sits at the same visual altitude as a
phase. ⭐ That is the §4.6 **role-lift**, and it is deliberate: the chevron IS the role selector.
⚠ The report does NOT inherit that lift — `WorkflowReportBuilder` groups strictly by
`SpectralWorkflowPhaseType`, so on paper Reference and Sample both appear under one **Acquisition**
heading. ⇒ **the chevron and the PDF disagree on what a "section" is.** ⛔ Not by design, as first written
here: they are two decisions taken years apart and never reconciled — see **§27.14a**, which asks whether
the report should carry step sub-headings and answers *yes, but never by importing the nav policy*.

#### 📐 27.13g THE DIAGRAMS  *(spectracs-docs)*

⭐ Two diagrams are the deliverable of this review, because the confusion was structural, not local:
- **`monitored_capture_sequence.puml`** — the sequence from the Measure click to the embedded
  `workflow.json`: who calls whom, where the one view object is built, and the two surfaces it reaches.
- **`monitor_record_model.puml`** — the object model: `MonitorRecord` and its rows, `MonitorResult`,
  the `TabGroupView` tree, and where each lives (transient / persisted / on paper).

⛔ Both must show the DEFECTS of §27.13b–c as marked notes until they are fixed, or the diagram will
document an intent the code does not have — the same mistake as the plugin comment.

### ⭐⭐ 27.14 RUBBER-DUCK PASS ON D1–D3 — walked against the code before writing any of it  *(2026-08-17)*

⭐ Same discipline as §19 / §21 / §23 / §25: read the call sites first. **W6 is the one that matters** —
it is a hole that already exists and that D1 makes reachable.

- ⛔ **W1 THE HEADING MUST BE COMPUTED AFTER THE FILTER.** `visitTabGroup` prints the tab label and *then*
  dispatches. Filter first, print the label only if at least one child survived — otherwise D1 replaces
  three curve pages with three bold orphan headings.
- ⛔⛔ **W2 `isMonitorView` HAS NO CLASS-LEVEL DEFAULT.** It is only ever assigned by the engine, and every
  reader uses `getattr(item, "isMonitorView", False)`. A `toJson()` written as `self.isMonitorView` would
  therefore raise `AttributeError` on the PROCESSING raster group — a view that has never been tagged.
  ⇒ declare `isMonitorView = False` on **`ReportableView`** (beside `isShownInReport`, one line, and it
  documents the concept once), then serialize it in `TabGroupView`.
- ⭐ **W3 NO ALEMBIC MIGRATION — and this time that is checked, not assumed.** `EvaluationResult.resultJson`
  is a `Text` **blob**; `isMonitorView` rides inside it. ⚠ §19/I7 made exactly this prediction about
  `monitorRecord` and was WRONG, because `SpectralWorkflow` is Option A (real columns) — the difference is
  real and it is the reason to state it: a workflow FIELD needs a column, a view-model field does not.
  ⇒ old rows simply read `False`, which is today's behaviour.
- ⛔ **W4 D1 AND THE PLUGIN'S OVERVIEW FLAGGING ARE ONE COMMIT.** Land the renderer alone and the settling
  section becomes **empty**; land the plugin alone and nothing changes. A tree that is briefly wrong in a
  way the tests can see is fine; one that prints a blank section is not.
- ⚠ **W5 ⛔ DO NOT TOUCH THE Qt RENDERER.** `ReportableView`'s contract is *"the host's report renderer
  includes only items whose `isShownInReport` is True; the GUI ignores the flag"* — and
  `QtWorkflowRenderer.visitTabGroup` correctly ignores it today. Two visitors, one flag, exactly one
  honours it. ⇒ say so in BOTH methods, or the next reader "fixes" the symmetry and deletes the Settling
  tab's curves from the screen.
- ⛔⛔ **W6 A CAPTURE NESTED IN A PRINTED GROUP IS DRAWN BUT NEVER ATTACHED.** `__collectGroups` calls
  `__prepareCapture` (assign `attachmentName`, take the PNG for `/EmbeddedFiles`) only for **top-level**
  `SpectrumCaptureView` items; `visitTabGroup` happily draws nested ones. ⇒ the page would show an image
  the machine payload does not carry, and its caption would silently lose the `[attachment: …]` marker.
  ⚠ It has never bitten because no tab group has ever been printed (§27.13b) — D1 is what makes the path
  live. ⇒ **decide before building**: either `__collectGroups` traverses groups (the bench already has
  `__flattenItems` doing exactly this traversal for the pixel fill — reuse the shape), or a capture inside
  a printed group is refused with one logged line. ⛔ Silently drawing it is not an option.
- ⚠ **W7 THE NEW SILENT FAILURE IS "FLAGGED BUT EMPTY".** After D1 a group whose children are all unflagged
  prints nothing, and that is indistinguishable from "the plugin declared nothing at all". ⇒ one greppable
  line, in the style of the CAPTURE-SETTINGS / MONITOR lines: `REPORT tab group '<title>' is flagged for
  the report but no child is`.
- ⚠ **W8 THE TESTS THAT MUST CHANGE, not just be added.** `test_tab_group_render.py`'s report assertion is
  `assertTrue(figures)` — a page carrying only a header satisfies it, so it cannot fail either before or
  after D1. ⇒ assert what was DRAWN (axes count / texts). ⭐ The D1 acceptance test is the measurement that
  found the defect: build the settling view from a canned record, render, assert **one page**, **zero
  `SeriesPlotView` axes**, and the metric grid present.
- ⚠ **W9 THE `_view`-TRANSIENCE COMMENT IS LOAD-BEARING** (D3). "Persist the view descriptor" is a
  plausible future change, and it would silently remove the settling tabs from every re-opened run. The
  test pins the behaviour; the comment explains why the test exists.

#### ⚠ 27.14a AN OPEN QUESTION EDWIN RAISED — should the report inherit the chevron's role-lift?

⛔ **A CORRECTION FIRST: §27.13f's "on purpose" was too strong.** Grouping the report by phase is
SPEC_bench_pdf_export.md's own decision (§1: *"grouped by phase, workflow order"*), written **before** the
role-lift existed (SPEC_simplified_plugin_navigation §4.6). They were two separate decisions that were
never reconciled — not one deliberate asymmetry.

⚠ **AND THE ASYMMETRY HAS A REAL COST**, which the settling section is what exposed: the Acquisition
section is now *reference full frame · reference ROI · reference spectrum · sample full frame · sample ROI
· sample spectrum · settling* — **seven items under one heading with no sub-structure at all**.

⛔ **FIRST ANSWER (SUPERSEDED, kept because the correction is the point):** *"give the report step
sub-headings and never let it see the navigation policy — `NavigationPolicy` is interaction chrome, and a
LIMS addon has no plugin loaded."* The coupling half of that is right. ⛔ The premise is not.

⭐⭐ **EDWIN'S COUNTER, AND IT IS THE BETTER ARCHITECTURE** *(2026-08-17)*: *"what I am not sure about is
that the NavigationModel should not be part of the Workflow itself — the plugin provides the info how
content is organized, and that structure would make sense independent of the plugin."*

⛔⛔ **THE FACT THAT SETTLES IT — the declaration does not survive its own run.** `NavigationPolicy` is
built by `plugin.policy()` and lives **only in the live host**: it is persisted nowhere, and
`AbstractPluginExecutionView._policy()` returns `WorkflowPolicy.default()` for any VIEW-mode run. ⇒ a
re-opened measurement shows **one `Acquisition` chevron instead of `Reference › Sample`** — it navigates
differently from how it was measured. ⚠ That is the SAME defect as everything else in §27.13: something
the plugin declared never reached the record.

⭐ **AND THE POLICY CONFLATES TWO DIFFERENT KINDS OF THING:**

| field | what it is | who may read it |
|---|---|---|
| `mode` (STEP / AUTO_ADVANCE) | pure **interaction** — "what happens when this capture finishes" | the live host only. ⛔ Meaningless on paper and to a LIMS addon |
| `stepChevronPhases` | **structure** — "in this workflow a step of ACQUISITION is a section in its own right" | ⭐ everyone: chevron, re-opened run, report, LIMS addon |

⇒ my "it is chrome" was true of `mode` and false of `stepChevronPhases`, and I generalised from the
wrong half.

⭐⭐ **REVISED D4 — PERSIST THE STRUCTURE ON THE WORKFLOW; READ IT EVERYWHERE.** The plugin still declares
it (nothing about ownership changes), the workflow CARRIES it, and every consumer reads it from the record
with no plugin present. ⭐ **This is not a new pattern — it is exactly `EvaluationResult`**: the plugin
declares view-models, the record carries them, hosts render them years later without the plugin. The
navigation structure is the one plugin declaration that was left out of that arrangement.
- ⭐ the chevron reads it ⇒ **a re-opened run navigates the way it was measured** (a real bug fixed, not
  just tidiness);
- ⭐ `WorkflowReportBuilder` reads it ⇒ *Reference* / *Sample* become sections under **Acquisition**, with
  the settling group under *Sample* where it was measured — and ⛔ still no plugin import, no policy
  object, no coupling. The report asks the RECORD, which is what it should always have done;
- ⭐ a LIMS addon gets the same structure for free.

⚠ **WHAT IT COSTS, stated plainly:**
- an **Alembic migration** — a column (or a field in an existing blob) on `SpectralWorkflow`. ⛔ Contrast
  W3: a workflow-level fact needs a column, a view-model field does not. This one is a workflow fact.
- ⭐ **RENAME IT.** Once the report reads it, "navigation" is the wrong word — and that word is precisely
  what misled the first answer into calling it chrome. It is a **section structure**: persist something
  like `sectionedPhases`, and let `NavigationPolicy` keep only `mode`.
- ⚠ the persisted declaration WINS on re-read even if the plugin has changed since. ⭐ Correct for a
  record — it says how THIS run was organised — but say it out loud.
- ⚠ ⛔ do NOT persist `mode`. Re-opening a saved run is browsing, not measuring; AUTO_ADVANCE is not a
  fact about the measurement. (It could ride along as pure audit; nothing would read it.)

✅⭐ **D4 IS ACCEPTED FOR IMPLEMENTATION** *(Edwin, 2026-08-17)*. ⛔ Still bigger than §27 — it belongs to
SPEC_simplified_plugin_navigation (owner of the concept), SPEC_bench_pdf_export (the consumer) and
persistence (the migration) — so it runs as its own phase set **G1–G5** (§27.17), separate from F1–F5, and
those specs must be updated with it. ⚠ It subsumes the "always sub-headings?" question the first answer
left open: the plugin's declaration answers it per workflow, so the report needs no convention of its own.

### ⭐⭐ 27.16 RUBBER-DUCK PASS ON D4 — and TWO findings change the shape of the work  *(2026-08-17)*

- ⛔⛔ **N1 `NavigationModel.stops()` IS DEAD CODE IN PRODUCTION — only the tests call it.** The chevron is
  actually built by `AbstractPluginExecutionView._rebuildPlan()`, which re-implements the same
  policy → stops derivation inline. ⇒ ⛔ **persisting the structure and teaching `NavigationModel` to read
  it would change NOTHING on screen.** ⚠ This is §27.11's lesson in another costume (*"guarding at the
  call sites is how the amber-cue bug survived a round"*): there are two implementations of one rule, and
  the tested one is not the live one. ⇒ **converge `_rebuildPlan` onto `NavigationModel.stops()` FIRST,
  as its own step, with the existing tests as the gate.**
- ⚠ **N2 THE DUPLICATION EXISTS FOR A REASON — the PREDICTIVE plan.** `_plannedPhases()` in NEW mode lists
  PROCESSING and EVALUATION *before they have any steps*, so the operator sees the whole road ahead;
  `stops()` can only see phases that already exist and skips empty ones. ⇒ convergence means **passing the
  planned phase list INTO `stops()`**, not deleting the prediction. ⛔ A naive merge silently shortens the
  chevron of every new run.
- ⛔⛔ **N3 THE STRUCTURE MUST RIDE IN `toReportJson()` TOO, not only in a DB column.**
  `diagnostics/report_reconstruct.py` rebuilds a workflow from the PDF's embedded JSON **with no DB and no
  plugin** — it is the exact plugin-free consumer D4 exists for, and a LIMS addon is the same shape. A
  column alone makes the claim only half true. ⚠ And the 124 archived reports carry no such field ⇒ the
  reconstructor must default to "no sub-sections", which means **a regenerated old report will not match a
  new one**. ⭐ Say that in the reconstructor's docstring beside the pixels/`attachmentName` caveat, where
  a reader already looks for exactly this kind of asymmetry.
- ⚠ **N4 SERIALISE IT AS A SORTED LIST OF ENUM VALUES.** `stepChevronPhases` is a `frozenset` of
  `SpectralWorkflowPhaseType`. JSON has no sets, and ⛔ iteration order of a frozenset must never reach the
  blob — two identical runs would otherwise produce different bytes and "same input, same record" dies.
- ⚠ **N5 A REAL ALEMBIC MIGRATION, on the APP db** (`./authorMigration.sh app "…"`), ⛔ in deliberate
  contrast to W3: a workflow-level FACT needs a column; a view-model field rides the blob. ⭐ Old rows read
  NULL → no lift → **exactly today's VIEW-mode behaviour**, so archived runs cannot regress.
- ⛔⛔ **N6 STAMP IT AT RUN START, NOT AT SAVE.** The other provenance fields (username, pluginCodeRef) are
  "stamped at Save" — copying that habit here would be a bug: **the bench renders the PDF preview in
  EVALUATION before anything is saved** (`__buildReportTab`), so the same run would print one way before
  Save and another way after. ⇒ stamp when the plugin is resolved (`_startNewRun`), so the in-memory
  workflow carries the structure from its first breath.
- ⚠ **N7 THE REPORT'S `groups` CONTRACT IS A FLAT LIST OF 2-TUPLES**, and tests call
  `render(reportView, [("PROCESSING", [view])])` directly. A heading LEVEL must be added tolerantly
  (accept 2- **or** 3-tuples) or those call sites break. ⛔ And `__drawPhaseHeading` **uppercases** — a step
  sub-heading must not, or "REFERENCE" shouts at the same volume as "ACQUISITION".
- ⚠ **N8 CHECK, DON'T ASSUME, THE VIEW-MODE ACQUISITION BRANCH.** With the lift restored in VIEW mode the
  wizard's `_renderStop` receives STEP stops for ACQUISITION; its branch
  (`isAcquisitionStep and not self._isView()`) sends them to `__computedPanel`, which is the very path that
  renders the settling tabs (§27.13d). ⇒ D4 should *improve* that path — one step per stop instead of all
  steps as tabs — but it changes what a re-opened acquisition looks like, so it is a click-through item.
- ⭐ **N9 THE PLUGIN SDK SURFACE DOES NOT CHANGE — no `SDK_VERSION` bump.** The host reads
  `policy().getNavigation().stepChevronPhases` once and stamps it; plugins declare exactly what they
  declare today. ⚠ That matters: §19/I2 established the gate is STRICT EQUALITY, so a bump would break
  every sealed M3 plugin for an API they do not use.

### ⭐ 27.17 D4, PHASED  *(G1–G5 — accepted, not built)*

```
 G1  MODEL     sectionedPhases on SpectralWorkflow (Text, sorted enum values)      [N4/N5]
               + toReportJson carries it + report_reconstruct reads it back        [N3]
               + Alembic revision on the APP db (./authorMigration.sh app)
               gate  persistence round-trip · report-JSON round-trip · NULL = today's behaviour
               risk  low, but it is the migration — review the generated file
 G2  CORE+APP  converge _rebuildPlan onto NavigationModel.stops(), predictive plan  [N1/N2]
               passed IN as the planned phase list
               gate  ⛔ ZERO behaviour change — the existing nav tests ARE the gate
               risk  THE structural step; do it alone, revert = one commit
 G3  APP       stamp the structure at _startNewRun (⛔ not at Save)                 [N6]
               chevron reads it from the WORKFLOW in both NEW and VIEW mode
               gate  a re-opened saved run reads `Reference › Sample`, not `Acquisition`
               risk  changes the re-opened acquisition layout — click-through item  [N8]
 G4  CORE      __collectGroups emits step sub-sections where the structure says so  [N7]
               render() accepts a heading level; ⛔ sub-heading not uppercased
               gate  Acquisition shows Reference/Sample; settling sits under Sample
               risk  the visible half — pairs with F2's PDF click-through
 G5  DOCS+RIG  update SPEC_simplified_plugin_navigation (owner) + SPEC_bench_pdf_export
               (consumer); click-through a re-opened run, then one PDF
```

⚠ **ORDER IS NOT NEGOTIABLE**: G2 before G3 (else the persisted structure changes nothing on screen — N1),
G1 before G3 and G4 (they read what G1 stores). ⭐ G2 is the only step with no visible effect, and it is
the one that makes the other three small.

### ⭐ 27.15 THE FIX, PHASED  *(D1–D4; none of it built)*

```
 F1  MODEL      isMonitorView default on ReportableView + TabGroupView (de)serialises it   [D2]
                gate: round-trip test asserts the tag survives · no migration (W3)
                risk: none — nothing reads it differently yet
 F2  CORE+PLUGIN  visitTabGroup honours CHILD isShownInReport; heading after the filter     [D1]
     (ONE commit) group prints its own title (27.13e); the flagged-but-empty log line (W7)
                  + plugin flags the Overview items shownInReport(True)                (W4)
                gate: one page · zero SeriesPlot axes · metric grid present (W8)
                risk: THE visible change — this is what the first PDF export will show
 F3  CORE       nested captures in a printed group: traverse in __collectGroups, or refuse  [W6]
                gate: a nested capture either gets an /EmbeddedFiles entry or is logged
                risk: decide the policy BEFORE writing it; F2 makes the path live
 F4  APP        D3 test through the real-DB persistence harness + the _view comment    [D3/W9]
                gate: save → reload → renderStep yields the six tabs
                risk: none (test + comment only)
 F5  RIG        the click-through §27.3 owes, THEN the first PDF export from a monitored run
                ⛔ must follow F2 — before it, the export documents a defect
 F?  OPEN       D4 step sub-headings in the report — Edwin's call, not scheduled
```

⚠ **F1 and F4 are independent of everything.** F2 is the only one that changes what a reader sees, and
F3 must be *decided* before F2 lands even if it is *built* after. ⭐ Four repos touched
(`-model`, `-core`, `spectracs-plugins`, `spectracsPy`) — the ordinary shape for this codebase.

### ⭐⭐ 27.18 COMBINED RUBBER-DUCK — F AND G TOGETHER  *(2026-08-17)*

⚠ **WHAT A THIRD PASS IS FOR.** §25.1 warned that a further pass over the same text mostly re-reads it.
⇒ this one deliberately looks only at what the per-track passes COULD NOT see: **F × G interactions**, and
the consumers neither track lists. It found four things worth the read; the rest of F and G survived
unchanged, which is itself a result.

- ⛔⛔ **Z1 THE REPORT MUST NEVER PRUNE THE VIEW OBJECT — and that decides HOW D1 is built.** It is
  tempting to filter in `__collectGroups` (a pure model pass, where both heading levels could then be
  computed exactly). ⛔ **It would break the screen**: §27.12's whole point is that the panel renders the
  SAME `TabGroupView` the report collects, so removing tabs for the report would remove them from the
  Settling tab bar. ⇒ **filtering stays at RENDER time** (D1 as written), and the emptiness question at
  both heading levels is answered by a shared pure predicate — `willDraw(item)` beside `dispatchItem` in
  `WorkflowItemVisitor`, defined as *"a flagged item, or a group with at least one flagged child"*.
  ⭐ One predicate, used by W1's tab label and G4's step sub-heading; ⛔ never two emptiness rules.
- ⛔ **Z2 FOUR HEADING LEVELS ON ONE PAGE, once both tracks land.** F2 gives the group its own title
  (§27.13e) and G4 gives the step a sub-heading, so the settling page would read
  **ACQUISITION › Sample › Settling › Overview** before a single number. ⚠ Neither track can see this
  alone. ⇒ budget **three**: phase (upper) · step (title case) · tab label (muted small), and ⛔ **drop the
  group's own title when the group is the only flagged item of its step** — which is exactly the settling
  case. §27.13e's cosmetic fix therefore becomes conditional, not unconditional.
- ⭐⭐ **Z3 THE ARCHIVE IS SAFE — BY CONSTRUCTION, AND IT IS WORTH KNOWING WHY.**
  `diagnostics/regenerate_reports.py` rewrites all 124 archived reports **in place** from their embedded
  JSON, and `settling_sweep.BASE` is that same folder — so SPEC_metric_research §10's numbers are computed
  from files this tool rewrites. ⇒ a layout change is not a small blast radius. ✅ But: **F2 cannot touch
  the archive** (no archived report contains a printed tab group — the settling group did not exist and
  the raster group is not flagged), and **G4 cannot either** (archived JSON carries no `sectionedPhases`,
  and its absence means "no sub-sections" — N3/N5). ⛔ And neither track changes a single computed number:
  they change what is PRINTED, never what is measured. ⇒ no regeneration is required by either track, and
  if one is run for other reasons the archive's numbers are unaffected.
- ⚠ **Z4 THE LAB GETS THE SAME ARTEFACT.** `pdfBytes()` is the LIMS publish path
  (`DevMeasurementBenchViewModule:465` → `SenaiteGateway`), so F2 and G4 change what SENAITE receives, not
  just what is saved locally. ⇒ the rig gate must include **one publish**, not only one local export.
- ⚠ **Z5 WRITE F4's TEST AGAINST THE RENDERER, NOT THE HOST.** G3 changes how a re-opened acquisition is
  laid out (N8). If F4's saved-run test drives the wizard it will need rewriting three phases later; if it
  asserts `renderStep(step)` — which is what actually carries the guarantee — G3 cannot invalidate it.
- ✅ **Z6 F1 AND G1 DO NOT COLLIDE.** F1 adds no column (blob field, W3) and G1 adds one (N5), so the
  autogenerated revision cannot sweep F1 up. ⚠ Standing hazard, not a new one: `--autogenerate` diffs the
  WHOLE metadata, so review the generated file (already G1's gate).
- ✅ **Z7 NOTHING IN EITHER TRACK TOUCHES THE MEASUREMENT.** No evaluator, no gate, no threshold, no
  spectrum. ⇒ ⛔ neither track can invalidate §11, the settling algorithm, or any archived number — the
  one property worth confirming out loud before a nine-step plan.

### ✅⭐⭐ 27.20 BUILT — F1–F4 AND G1–G4, 2026-08-17  *(416 tests green; only the rig session is left)*

| step | what landed | gate, measured |
|---|---|---|
| **F1** | `isMonitorView` defaults on `ReportableView`, (de)serialised by `TabGroupView` | the tag survives a real save/reload |
| **F4** | `tests/test_saved_run_shows_the_settling_tabs.py` + the `_view`-transience comment in `renderStep` | live → capture panel · reloaded → the six tabs |
| **G1** | `sectionedPhasesJson` + `toReportJson` + `report_reconstruct`, migration **`cb8c2942a6bc`** | DB + report-JSON round-trips; NULL = pre-D4 |
| **G2** | `_rebuildPlan` delegates to `NavigationModel.stops(plannedPhases=…)`; the view's private label copies deleted | ⛔ zero behaviour change; the nav tests were the gate |
| **F3** | `__collectGroups` descends into printed groups; ⭐ **and attachment names are unique** | a nested capture reaches `/EmbeddedFiles` |
| **F2** | `willDrawInReport` + `visitTabGroup` honours it; heading after the filter; flagged-but-empty logged | ⭐ **3 pages → 1 page, 0 curve axes, the summary intact** |
| **G3** | stamped in `_startNewRun`; the chevron reads `workflow.getSectionedPhases()` | a re-opened run still reads `Reference › Sample` |
| **G4** | step sub-sections; `render()` takes a heading level; ⛔ not uppercased | *Reference* / *Sample* under **ACQUISITION**, settling under *Sample* |
| **G5** | §4.6a in SPEC_simplified_plugin_navigation, §3a/§3b + the naming warning in SPEC_bench_pdf_export | — |

⛔⛔ **ONE MORE DEFECT, FOUND WHILE BUILDING F3 AND OLDER THAN ALL OF THEM.** `__prepareCapture` named the
`/EmbeddedFiles` entry from the step's ROLE alone, but an acquisition step declares **two** reportable
captures (full frame + cropped ROI) — both were `capture_sample.png`, and `pypdf` keeps one entry per name.
⇒ **MEASURED: three captures on one step produced a single attachment.** Every report the app has ever
written has been dropping its cropped frame from the machine payload while printing it on the page. The
first capture of a role keeps its historic name; the rest are suffixed. ⚠ A reconstructed archived report
arrives with `attachmentName` already set from its own JSON, so the archive's names are untouched — Z3
holds.

✅ **W4's HAZARD DID NOT EXIST.** `__settlingSummary` already ends with `item.setShownInReport(True)` on
every Overview row, so F2 was renderer-only and the summary was never at risk of vanishing. ⭐ Checked by
running it, not by reading it — which is how the three-page measurement was made in the first place.

✅ **PARTLY CONFIRMED IN THE APP** *(Edwin, 2026-08-17)*. A PDF from a monitored run **has now been read on
paper** — that is what produced §27.21 (the curves were missing) and §27.22 (the gate panel was cut off,
the double heading, the orphaned title), and both were fixed against the rendered pages. The status bar was
driven again after §27.24 and reported **"works so far"**.

⚠ **STILL OWED — the rest of the rig session (step 10):** a **re-opened saved run** (does the chevron read
`Reference › Sample`, and do the Settling tabs come back?), **one LIMS publish** (Z4 — `pdfBytes()` is the
SENAITE path, so the lab receives the reshaped document too), and ⚠ **one more PDF read after §27.22**,
since the pages that were looked at still had the layout faults in them.

### ⭐⭐ 27.21 ALL THREE CURVES GO ON PAPER — a flag that outlived its reason  *(Edwin, 2026-08-17, from the first report)*

⭐ **Edwin, reading the first PDF written under D1: *"the overview tab is rendered in the pdf but not the
tabs with the graphs"* → *"I want all 3 graphs to be rendered in the report."*** ✅ IMPLEMENTED.

⛔⛔ **THIS IS NOT A REGRESSION FROM D1 — IT IS A STALE FLAG, AND THE SEQUENCE IS WORTH KEEPING.**

| when | state | why |
|---|---|---|
| §18.8 / §27.8 | graph tabs `shownInReport = False` | Overview was the **combined chart**, so flagging them would print the same three curves **twice** |
| §27.9 | Overview becomes a **TEXT summary, no chart** | Edwin at the rig — three stacked panels left every one of them too short |
| ⛔ *(nobody came back)* | the flags stayed | the duplication that justified them no longer existed |
| §27.13b | the renderer ignored the flags anyway | so the defect and the stale flag **cancelled out** — the curves printed, for the wrong reason |
| D1 | the renderer honours the flags | ⇒ the report suddenly carried **no curve at all** |
| **§27.21** | the graph tabs are flagged **True** | the curves are back, now for the right reason |

⭐⭐ **§18.6 IS WHY IT MATTERS**, and it had quietly become false twice over: *"a `Q%` in a report that
carries its own settling curve is a different object from a bare number — it shows the reader that the
value was CHOSEN, when, and on what evidence."* A summary that only STATES `readAs: VERTEX` asks the reader
to take that on trust; the curve shows it.

⚠ **WHAT DID NOT CHANGE — and this is D1 still doing its job.** `Health` and `Decisions` remain
`shownInReport = False` and stay off paper: §18.8's *"a miller's report never carries a page of empty
diagnostics"* is about the 34-row decision arithmetic, not about the curves. ⇒ the flag is now carrying a
real distinction rather than a stale one, which is the difference between a working mechanism and a
coincidence. **Measured: 2 pages — summary + Q% on the first, Turbidity + Rate on the second, no tables.**

⭐ **THE LESSON, because it is the third time in §27**: a rule whose *justification* is deleted by a later
decision does not delete itself. §27.9 reversed the thing §27.8's flag depended on, and the flag survived
its own argument for nine days. ⇒ when a reversal lands, grep for what cited the old behaviour.

### ⭐ 27.22 THREE LAYOUT FAULTS THE CURVES EXPOSED  *(Edwin, from the first report that carried them, 2026-08-17)*

⭐ *"works fine, but some graphs is cut-off at the left"* — and looking at the rendered pages to fix it
turned up two more that the same screenshot contained. ✅ All three fixed; 419 tests green.

- ⛔⛔ **THE AXES RECT IS NOT WHERE THE LABELS ARE.** A plot's rect starts AT the content margin, but
  matplotlib draws the tick labels and the rotated y-label **outside** it. MEASURED on the gate panel
  (`|Δ A_valley / Δt| (the gate)` over ticks like 0.00175): leftmost label at figure **x = −0.000** —
  printed past the paper's edge.
  ⇒ series panels keep a fixed left **gutter**, and every plot gets a measured guard behind it.
  ⚠ **A CONSTANT FOR THE GUTTER, MEASUREMENT FOR THE GUARD, and the split is the point.** A per-plot fit
  would give each panel its own left edge — and the three settling curves are SEPARATE view-models
  rendered in separate calls, so the stack would step down the page. Alignment needs one shared number;
  the measured guard then only has to catch what that number does not cover.
  ⚠ The guard **triggers on the page edge but corrects to the content margin**: triggering on the margin
  would nudge every spectrum plot in the app (they measure 0.034 — inside the paper, outside the margin,
  and that is how all 124 archived reports were drawn), so a regenerated archive would shift for cosmetics.
- ⚠ **THE SAME HEADING TWICE.** Each per-graph tab is a `SeriesPlotView` that carries its own title, so
  paper printed the tab label AND the title: literally **"Q%" over "Q%"**, and for the others a short name
  above the real one (*Turbidity* / *A_valley 500–560 nm*). ⭐ On SCREEN this reads fine — a tab bar and a
  plot are different furniture — which is why it survived: ⛔ the flattening is what makes them adjacent.
  ⇒ **a tab whose single child titles itself lets the child name it**, and the child's title wins because
  it carries the units. Tabs of untitled children (the raster captures, the Overview column) keep theirs.
- ⚠ **AN ORPHANED TITLE.** Block-by-block flow left *A_valley 500–560 nm* alone at the foot of one page
  with its curve on the next. ⇒ a titled series plot reserves **title + header lines + first panel as one
  lump**, so the page breaks BEFORE the title rather than after it.

⭐ **THE COMMON THREAD, worth naming: all three are the flattening tax.** Tabs are furniture on screen and
they become bare stacked blocks on paper — the label that read as a tab becomes a heading, the plot that
sat inside a frame becomes a block that can be split, and the margin that framed a widget becomes the edge
of a sheet. ⇒ ⚠ **whenever a screen container is flattened for print, re-read the RENDERED PAGE, not the
diff.** Every one of these was invisible in the code and obvious in the image.

### ⭐⭐ 27.23 THE INDETERMINATE BAR — WHY IT HAS NO STRIPES AND WHY IT STOPS  *(Edwin, 2026-08-17; DESIGN, not built)*

⭐ Two complaints, two unrelated causes, and the rubber-duck pass found that **the fix Edwin chose would
have reproduced one of them**. Decisions: ✅ the **emitter fix**, ✅ a **fade** bar
(`pyqt-loading-progressbar`'s technique) in the brand green.

#### ⛔⛔ P1 THE STRIPES ARE NOT MISSING FOR LACK OF CONTRAST — the app's OWN stylesheet destroys the gradient

`ApplicationStyleLogicModule`'s global sheet carries `QProgressBar::chunk { width: 1px; … }`. That makes Qt
tile the chunk in **1-pixel segments and map the gradient into each segment**, so every segment paints the
gradient's first colour and the bar is one flat green that merely shifts shade as the phase moves — which
is exactly what Edwin described.

⭐ **MEASURED** (render to a pixmap, count colours across the middle row of a 400 px bar):

| | distinct colours | colour runs |
|---|---|---|
| widget sheet alone | 3 | **11** — ten clean stripes |
| with the app-global QSS | **1** | **1** — flat |

⛔ My first guess — "low contrast at a fine pitch" — **was wrong**, and tuning the greens would have
produced a slightly different flat green.

#### ⭐⭐ P2 THE FADE WOULD HAVE BROKEN THE SAME WAY — this is what the pass is for

The fade is *also* a `::chunk` gradient (transparent → colour → transparent). **MEASURED** with the global
sheet applied: **3** distinct colours, flat; with it off: **170**. ⇒ swapping the widget without P3 would
have reproduced the complaint against a brand-new implementation, and the obvious conclusion would have
been "the new widget doesn't work either".

#### ⭐ P3 THE FIX IS ONE LINE, AND IT IS PROVABLY INVISIBLE EVERYWHERE ELSE

Deleting `width: 1px` from the global chunk rule renders an ordinary determinate bar **pixel-identical** —
verified by comparing the full colour-run sequence of a 60 %-filled bar, with and without: `IDENTICAL`.
It is the classic segmented-bar trick with no spacing to make segments visible, i.e. dead styling that
does nothing but break gradients.
⛔ **Rejected: a local override.** `width` would then have to track the bar's pixel width on every resize —
MEASURED: `width: 400px` on a 700 px bar tiles the fade **twice**. A global deletion has no such state.

#### ⚠ P4 THE STALL IS THREE EMITTERS — and one of them is not a bug

| emitter | what it does | verdict |
|---|---|---|
| `__onAutoExposeProgress` | determinate `stepsCount = totalProbes` | ⭐ **correct** — the sweep HAS a real fraction (n/N probes), and showing it beats animating |
| `__onAutoExposeFinished` → `__clearStatus()` | `isStatusReset` → "ready for action…" | ⛔ **the bug** — resets the bar to idle in the middle of a capture |
| *(nothing)* after AE | silence until the first frame or row | ⛔ ~43 s on the monitored path at W = 60 |

⇒ **THE RULE: a capture OWNS the status bar from the click to its end, and nothing inside it may RESET
it.** A sub-step may refine the bar (AE's real fraction) and must then hand ownership back, not drop it.

#### ⚠ P5 AE ALSO RUNS OUTSIDE A CAPTURE

The auto-exposure checkbox path runs the sweep on its own, and there `__clearStatus()` is exactly right.
⇒ the fix is conditional on `self.__capturing`, ⛔ not a deletion.

#### ⚠ P6 THE FADE ANIMATES `value`, WHICH COLLIDES WITH THE DETERMINATE PATH

The animation drives the bar's own `value`, so it must be STOPPED before any real `setValue` — the same
pairing `__stopStripes()` has today, and for the same reason. ⛔ And no `%p` / `%v` in the format while it
runs: the percentage would jitter with the animation. Today's formats are literal; keep them so.

#### ⚠ P7 THE EXISTING TESTS PIN THE MECHANISM, NOT ONLY THE BEHAVIOUR

`tests/test_status_bar_indeterminate.py` asserts `_stripeTimer`, `__advanceStripes`, `"qlineargradient" in
styleSheet()` and `value() == maximum()`. ⭐ The BEHAVIOURAL half survives untouched (the text is kept, the
range stays 0..100, the animation stops on determinate / reset / guidance). ⚠ `test_the_stripes_actually_move`
**inverts**: with the fade the stylesheet is set ONCE and the VALUE moves.

#### ⭐ P8 THE TEST THAT WOULD HAVE CAUGHT THIS DOES NOT EXIST YET

Every current test asserts on the stylesheet STRING — which was correct all along. ⇒ add the one that can
see a collapsed gradient: **render the bar to a QPixmap with the real application stylesheet applied and
count distinct colours across a row.** ⚠ That is also the only test that can fail if someone re-adds
`width: 1px`.

#### ⚠ P9 THE PACKAGE ITSELF IS NOT TAKEN

`pyqt-loading-progressbar` is **PyQt5** (a different binding — two Qt libraries in one process) and a
non-starter for the buildozer/p4a Android build. ⭐ It is **MIT and 29 lines**, so the TECHNIQUE is ported
with attribution in a comment and no dependency is added: a static gradient plus a `QPropertyAnimation` on
`value`, ping-ponged Forward/Backward. ⭐ That also deletes the 70 ms timer and the per-tick
`setStyleSheet` — a full style re-polish 14×/s, only ever to shift a gradient.

### ✅⭐ 27.24a BUILT — B1–B4, 2026-08-17  *(423 tests green; only the rig pass is left)*

| step | what landed | gate, measured |
|---|---|---|
| **B1** | `width: 1px` deleted from the app-global `QProgressBar::chunk` | gradients survive the global sheet (1 run → 11); an ordinary bar unchanged |
| **B2** | `__onAutoExposeFinished` hands the bar back while `__capturing`; a re-emit after the bounded AE wait; the monitored path announces "filling the first window …" | no reset signal between click and end; a standalone sweep still resets |
| **B3** | fade: one static gradient + `QPropertyAnimation` on `value`, ping-ponged; greens from `ApplicationStyleLogicModule` | sheet written ONCE · animation stops on determinate/reset/guidance · text kept |
| **B4** | `test_status_bar_indeterminate.py` rewritten + `test_capture_owns_the_status_bar.py` | see below |

⛔⛔ **THE PIXEL TEST WAS VACUOUS ON ITS FIRST ATTEMPT — and it is the whole point of B4.** Written as
"render the bar and count distinct colours", it PASSED with `width: 1px` deliberately put back. The cause:
the format text is drawn across the middle of the bar and its **antialiased glyph pixels** contribute ~20
colours by themselves — measured **26** with the defect in place, sailing past any threshold while the
chunk behind them was provably flat. ⇒ the text is hidden for the measurement, and the test was then
re-run against the restored defect and **failed at "collapsed to 2 colour(s)"** before the fix went back.
⭐ A test that cannot fail is worse than no test (§27.12) — this file has now produced that lesson twice,
so the verification step is not optional: **re-introduce the defect and watch the new test go red.**

### ⭐ 27.24 THE BAR, PHASED  *(B1–B5 — B1–B4 BUILT, B5 owed)*

```
 B1  STYLE    delete `width: 1px` from the app-global QProgressBar::chunk rule      [P1/P3]
              gate  an ordinary bar renders PIXEL-IDENTICAL (measured) · stripes appear
              risk  touches every progress bar in the app — the pixel test IS the control
 B2  CAPTURE  a capture owns the bar: ⛔ no __clearStatus() while self.__capturing,  [P4/P5]
              and an indeterminate re-emit after the sweep ("waiting for the first window …")
              gate  no reset signal between the click and the capture's end
              risk  ⚠ AE outside a capture must still reset — condition, do not delete
 B3  WIDGET   fade: ONE static gradient + QPropertyAnimation on `value`, ping-pong   [P9/P6]
              greens from ApplicationStyleLogicModule; ⛔ stop it before any real setValue
              gate  the sheet is set once · the animation stops on determinate/reset/guidance
              risk  the visible change; ⛔ MUST land after B1 or it looks broken      [P2]
 B4  TESTS    rewrite the mechanism assertions; ⭐ add the RENDERED-PIXEL test        [P7/P8]
              gate  the pixel test fails if `width: 1px` ever comes back
 B5  RIG      one reference capture (with AE) + one monitored sample
              gate  the animation never stops between click and end; the fade is visible
              ✅ Edwin 2026-08-17: "works so far"
```

⛔ **B1 BEFORE B3** — the whole point of P2. ⭐ B2 is independent of both and is the actual complaint;
it could ship alone.

### ⛔⛔ 27.25 THE DISCARDED MEASUREMENT — the vertex winner outlives its own spectrum  *(2026-08-18)*

⭐ Edwin, after the first two real measurements: *"after capturing the sample i get always or sometimes
[a dialog] saying 'could not capture'… first measurement was in fact 14.38 and i had to repeat the capture
due to the 'could not capture' thing and it raised to 14.8."*

⛔⛔ **A SUCCESSFUL RUN IS BEING THROWN AWAY, AND THE REPEAT IS BIASED UPWARD.** Every frame arrived, the
gate fired, the answer was computed — and the app reported *"Capture failed — no frames were delivered by
the camera"*, which is not merely unhelpful but false.

#### The mechanism, measured

`MonitorEngine.__pruneSpectra` keeps the reduced mean spectrum of the last
`SPECTRUM_RETAIN_DECISION_ROWS = 5` decision rows and protects the promoted row via `__promotedRow()` —
which returns `None` until `__answer` is latched, i.e. **the winner is unprotected during exactly the
window in which it can still be pruned.** On the vertex branch the winner is not the current row
(`promoteRow = usable[minimumIndex]`).

⭐ Driven against the REAL engine with a stub evaluator that promotes N decision rows back:

| promoted row | answer | spectrum |
|---|---|---|
| 0 – 4 rows back | set | PRESENT |
| **5 rows back** | set | **⛔ None** |
| 6, 9 rows back | set | ⛔ None |

⇒ `result.spectrum is None` ⇒ `captureMonitoredStep` sets no container ⇒ `CapturePanel`'s
`spectrum is None` guard fires the failure dialog.

⭐⭐ **TO THE QUESTION EDWIN ASKED — IS A FALSE SPECTRUM TAKEN? NO.** The engine reads `winner.spectrum`
and there is no substitution path anywhere: it is a MISSING spectrum and a DISCARDED measurement, never a
wrong number. ⚠ And the history genuinely is not kept — only 5 decision rows hold a spectrum, and the
record itself stores rows as numbers, never spectra.

#### ⛔ WHY IT IS A CADENCE BUG, and why every test passed

| | |
|---|---|
| Edwin's rig | ~3.5 fps ⇒ a decision row every **17.1 s** ⇒ 5 retained rows = **85 s of history** |
| jar B's curve | the `Q%` minimum sits **3.27 min** before the gate confirms it |
| at the diagnostic's 3.28-min sampling | that is **1.0** decision rows back — safe, and it is what the tests replay |
| at the live 17.1-s cadence | that is **11.5** decision rows back — far outside the window |

⇒ **a window sized in ROWS, validated at one cadence, used at an 11× finer one.** The retention comment
even states the assumption it broke: *"the vertex reaches ~2 decision rows back"*.
⚠ **And each half is tested, the seam is not**: `test_clearing_evaluator.py` drives the evaluator alone and
correctly asserts `promoteRow.t ≈ 16.655`; `test_monitor_engine.py` drives the engine with a fake evaluator
that always promotes the CURRENT row. Nobody tested *evaluator nominates an old row × engine has pruned it*.
⇒ it fires **always on a fill that clears** (vertex branch) and **never on one that arrives clear**.

#### ⛔ WHAT IT COST — the first two measurements are not what they appeared to be

Both archived runs read `arrived-clear`, i.e. **both are repeats**: the first attempt failed, the lamp
cleared the jar in the process, and the second attempt measured a fill that had already banked dose.
⇒ ⛔ **the σ_fill of 0.696 computed from them is void** — it is fill scatter plus two unknown doses, and
the earlier conclusions drawn from it (3.3× the refill floor, the tracker-band arithmetic) are withdrawn.
⚠ The record could not reveal this: a `MonitorRecord` has no field saying *this fill had already been in
the beam*, so a repeat is indistinguishable from a fresh fill after the fact.

#### ⭐ DECISIONS

- ⭐⭐ **A RUN THAT PRODUCED AN ANSWER IS NEVER REPORTED AS A FAILED CAPTURE.** Whatever the cause, the
  answer plus its trajectory must reach the operator; a missing spectrum is a degraded result, not a
  non-result.
- ⭐ **RETENTION IS SIZED IN TIME, NOT IN ROWS** — enough to cover `maxSeconds`, derived rather than
  chosen. ⛔ Edwin proposed "200 or so"; at the new 5-s cadence 200 rows is **1000 s = 16.7 min**, still
  short of the 25-minute cap ⇒ a fixed row count would leave exactly this class of bug alive.
  ⚠ Cost at the cap: ~300 rows × ~30 KB ≈ **9 MB**, which Edwin has explicitly accepted.
- ⚠ **THE RECORD GAINS A RE-MEASURE FLAG** — a fill that has been in the beam is a different sample
  (§17/U2), and the number must carry that.

### ⭐ 27.26 THREE PARAMETER CHANGES  *(Edwin, 2026-08-18 — DESIGN, not built)*

#### ⭐ θ = 0.005 /min *(was 0.0017)*

Replayed through the real `ClearingEvaluator` on jar B, the one curve that actually cleared:

| θ | promoted at | `Q%` read | vs the true minimum |
|---|---|---|---|
| 0.0017 | 23.21 min | 13.2733 | −0.0011 |
| **0.0025 … 0.010** | **19.93 min** | **13.2733** | −0.0011 |

⇒ **3.3 minutes of lamp exposure saved and the answer is bit-identical**, because the value is protected by
the VERTEX read while θ only decides when to stop looking. The gain saturates at 0.0025, so **0.005 sits
mid-plateau rather than at its edge**. ⚠ One curve, sampled at 3.28 min — record it as *"≥0.0025 saturates
on jar B; 0.005 chosen with margin"*, ⛔ not as a derived optimum. ⚠ On Edwin's own two runs θ changes
nothing at all (0.0017 → 0.006 all promote at 107.9 s): those arrived clear, and their delay is §14.2a's
structural three-window minimum.

#### ⭐ A DECISION ROW EVERY 5 s *(was every W frames ≈ 17 s)*

⭐ **IT IS FREE IN CPU.** `evaluateEveryNFrames` is already **1** — every frame is already reduced and
evaluated — so the decision cadence is a LABELLING rule, not a work rule. Denser rows add no computation;
they add persisted rows (~300 vs ~88 over the cap, ≈ 45 KB in the blob).

⚠ **IT IS FREE FOR THE GATE**, too: §14.3's comparison is span-based (`GATE_SPAN_SECONDS = 70`, walking
back until the span is met), which is exactly the property that stopped adjacent rolling rows from firing
the gate. Row spacing cannot break it.

⛔ **WHERE IT DOES COST — the minimum is SELECTED over more candidates.** Simulated 200× with real
overlapping windows and per-frame noise calibrated to the measured 0.063 window floor:

| cadence | decision rows | vertex bias | vertex sd |
|---|---|---|---|
| 17.1 s | 87 | −0.115 | 0.029 |
| **5.0 s** | 289 | **−0.136** | 0.031 |

⇒ **+0.021 `Q%` of extra downward bias** — 10 % of the refill floor, an order of magnitude below fill
scatter. **Affordable.**
⛔ **AND THE FIX I EXPECTED TO NEED IS NOT NEEDED.** The worry was that three ADJACENT rows 5 s apart share
~70 % of their frames and would make the parabola ill-conditioned. Measured: choosing the vertex's
neighbours by TIME instead (17 s or 35 s apart) changes the bias by **0.0007** — nothing. The fit is not
the problem; the selection is. ⇒ ⛔ do not "fix" the vertex neighbours.
⚠ **A side finding, recorded not acted on:** in this simulation the vertex is **not** measurably better
than the raw minimum (−0.115 vs −0.111), and BOTH carry a ~0.12 downward bias that no budget mentions.
§2.2 claims the vertex averages away the raw minimum's selection bias; on a curve this flat it does not,
because the three points are themselves selected around the excursion. Worth its own measurement.

#### ⭐ RETENTION derived from the cap *(Edwin: "200 or so … no problem concerning memory")*

Accepted in spirit, ⛔ not as a row count — see §27.25's decision. Sized in seconds, it cannot be
invalidated by the very cadence change made in the same breath.

```
 ✅ M1  SDK     retention sized in TIME (cover maxSeconds)                       BUILT 2026-08-18
 ✅ M2  SDK     θ 0.0017 -> 0.005                                                BUILT 2026-08-18
 ✅ M3  HOST    never report "capture failed" for a run that produced an answer  BUILT 2026-08-18
 ✅ SEAM TEST   evaluator nominates an old row × engine has pruned it            BUILT 2026-08-18
 ⚠ M4  RECORD  a re-measure flag on MonitorRecord; the fill's exposure history travels with the number
 ⚠ M5  RIG     one MUDDY fill (the vertex branch — the case that has never once completed) + two fresh
               fills measured ONCE each, for the first honest σ_fill
 ⚠ 5s  SDK     the 5-second decision cadence — DELIBERATELY HELD until M5 confirms a muddy fill completes
```

#### ✅ 27.26a AS BUILT — 428 tests green  *(2026-08-18)*

| | |
|---|---|
| **M1** | `SPECTRUM_RETAIN_DECISION_ROWS = 5` → a horizon of `policy.maxSeconds`. The stub-evaluator probe now keeps the winner's spectrum at **0, 1, 4, 5, 6, 9, 40 and 120** decision rows back (it died at exactly 5 before) |
| **M2** | `THETA_PER_MINUTE = 0.0017 → 0.005` |
| **M3** | the engine falls back to the newest decision row that still has a spectrum and records a note; the host ⛔ never claims "no frames were delivered" about a run that answered |
| seam | `tests/test_the_winner_keeps_its_spectrum.py` — verified by re-introducing the 5-row prune: **3 of its 4 tests go red**, with the message naming the consequence |

⛔⛔ **AND θ = 0.005 HAS A COST THE REPLAY DID NOT SHOW — found by a test that failed.** §14.3's acceptance
test asserts the rate form reproduces the 2026-08-14 criterion, whose gate confirms at **19.93 min**. At
θ = 0.005 the gate fires at **13.38 min** — *before* the fill's own `Q%` minimum at 16.66, i.e. **the gate
now declares "stopped clearing" while the fill is demonstrably still clearing.**
⭐ The ANSWER is unharmed: `__afterGate` refuses to read a minimum with no row on its far side, so
promotion still lands at 19.93 with the identical 13.2733 — which is why the earlier replay saw only the
benefit. ⛔ But `clearingSeconds` is logged as a σ_fill component (§2.4) and now means *"when the gate said
so"* rather than *"when the fill stopped clearing"*. ⚠ A number that travels in the record has quietly
changed meaning; that is recorded here rather than smoothed over.
⇒ the original test keeps its guarantee, pinned at **θ = 0.0017 — the θ that equivalence is about** — and
`test_the_shipped_theta_saves_dose_and_reads_the_SAME_value` pins both halves of the trade Edwin accepted,
including the early gate. ⛔ Neither test may be "fixed" by moving it to the other θ.

⚠ **One more hard-coded constant found and bound**: `test_settling_views.py` asserted the literal `0.0017`
where it meant *"the criterion is drawn on the rate axis"* — it now asserts
`ClearingEvaluator.THETA_PER_MINUTE`, so the next θ change cannot break a test that is not about θ.

⛔ **M3 before M5**, or the rig session cannot produce a clean fill: today every clearing fill is
discarded and re-measured, which is what contaminated the first two.

### ⭐ 27.19 THE COMBINED LANDING ORDER  *(F + G, ten steps)*

```
  #   track  step                                              depends on   visible?
  1   F1     isMonitorView survives a save                     —            no
  2   F4     saved-run render pinned by a test  (Z5)           —            no
  3   G1     sectionedPhases + toReportJson + migration        —            no
  4   G2     converge _rebuildPlan onto NavigationModel.stops  —            ⛔ must be no
  5   F3     nested-capture policy DECIDED (built here or not) —            no
  6   F2     tab groups honour child isShownInReport           F3 decided   ⭐ YES — the PDF
             + plugin flags the Overview items  (one commit)
  7   G3     stamp at run start; chevron reads the workflow    G1, G2       ⭐ yes — the chevron
  8   G4     report step sub-sections; 3 heading levels (Z2)   G1, F2       ⭐ yes — the PDF
  9   G5     SPEC_simplified_plugin_navigation + _bench_pdf_export updated  docs
 10   RIG    ONE session: the §27.12 click-through · a re-opened run ·
             a PDF export · ⭐ one LIMS publish (Z4)           F2, G3, G4   the gate
```

⭐ **1–5 change nothing a user can see** — five of ten steps are invisible, which is the same shape as
§21/M4's "large in VOLUME, not in RISK". ⛔ **The two orderings that are not negotiable**: G2 before G3
(N1 — otherwise the persisted structure moves nothing on screen), and F2 before G4 (they edit the same
collector/renderer pair, and G4's heading budget assumes F2's filter exists).
⚠ **The rig session is ONE session, not two** (Z4): F5 and G5's click-throughs are the same drive.

### ⭐ 27.3 WHAT IS DONE, AND WHAT IS STILL OWED  *(updated after the click-throughs of 2026-08-17)*

✅ **CLICK-THROUGH PASSED** *(Edwin: "now works as expected")* — the bench drives a real fill end to end:
the relabelling Cancel button, the live spectrum, the striped bar from the click onwards, the Settling
tab under Sample with its text Overview and per-curve tabs, and a settled answer with its record.

✅ **V1 IS CONFIRMED ON LIVE HARDWARE, AND IT RODE THE CLICK-THROUGH** (§23/V1 asked for exactly this).
The archive gave **82.0 % distinct frames at frameCount 150**; the bench reported ⭐ **87.9 % at
frameCount 60**. ⇒ duplicates are real, mild, and slightly *rarer* at the shipped burst size — so
§14.2b's budget holds with a little more margin than assumed (`W = 60` behaves like ~53 independent
frames). ⭐ And it is now recorded per run, so a drifting duplicate rate shows up by itself.

✅ ~~The settling summary no longer reaches the PDF~~ — **FIXED properly by §27.12**: the views hang off
the SAMPLE step they describe, so the report collects them under Acquisition with no new mechanism, and
`toReportJson()` carries the record too.

⚠ **STILL OWED**

⚠ **CLICK-THROUGH OF §27.12 — the click-through above predates it.** ⛔ The pass Edwin reported was on the
build where the panel constructed its own widget; the views now come from the SAMPLE step's
`EvaluationResult`, and the Settling tab is rendered from `result.views`. ⇒ **what needs re-checking is
exactly one thing: does the Settling tab still appear under Sample, with the same tabs and content?**
⭐ The offscreen tests cover attachment, non-duplication, the report section and the report payload — but
⛔ they cannot see a tab bar, which is precisely where the last three faults lived.
⚠ **A first PDF export from a monitored run** — the report path is asserted in tests but has never been
looked at on paper. ⭐ Expect the settling section under **Acquisition**, after the Reference/Sample images.
⛔ **AND EXPECT IT TO BE WRONG UNTIL §27.13b IS FIXED**: the renderer ignores child `isShownInReport`, so
today a monitored run prints Overview **plus all three curves plus both diagnostic tables** — measured at
**three pages** on a 12-row record, where §18.8 promised the summary alone.

⛔ **§27.13 D1–D3 — THREE FIXES, SPEC'D AND NOT YET BUILT**: honour child `isShownInReport` inside a tab
group (and flag the Overview items, or the summary vanishes); round-trip `isMonitorView`; pin the
saved-run render with a test. ⚠ D1 changes what the first PDF export will show, so it belongs **before**
that click-through, not after it.

⚠ **A rig run of `diagnostics/settling_run.py`** — the script has still never met a camera. It is the
P3 deliverable and the vehicle for §11.
⛔ **§11 itself — THE HEAT-DOSE EXPERIMENT (P4).** Everything built so far exists to make it measurable.

⏸ **§31.11b / C6 — THE TEST C RIG SESSION** *(added 2026-08-19)*. The whole of §31 is built and green, and
⛔ **all of it is derived from ONE archived run and has never met a camera.** Four arms, in order: a fresh
fill must NOT trip it *(⛔ a false positive stops the session)*, an aged fill should, the record must carry
the four new diagnostics, and the cold-holder arm probes the false-positive mode §31.9 leaves unmeasured.
⚠ Needs a dilution left standing overnight, undisturbed — that is the lead time.

---

## ⭐⭐ 28 · SERIES F — THE FIRST MEASUREMENTS THE PROTOCOL EVER PRODUCED  *(Lugitsch A, 2026-08-17/18)*

> Artifacts: `spectracs-references/tmp/2026ß817LigitschA/001…007.pdf`, each carrying its complete
> `workflow.json` — outcome, branch, policy, evaluator version and every decision row. Every number below
> was read back out of those artifacts, not transcribed by hand.
> ⚠ The folder name is a typo for `20260817_Lugitsch_A`; renaming it would break this reference, so it is
> quoted as it stands.

⭐ **WHY "SERIES F" AND NOT SERIES E.** §16.11.11 defines series E as *brown, 6 separate fills of one
stock, ~15 min each*. This is not that, and it does not replace it. It is the first σ_fill data taken under
a protocol where **the instrument decides when the sample is worth measuring** — which is the thing
§16.36 said had to exist before any reproducibility number meant anything. E's design still stands; F is
what the protocol produced the first night it ran.

### ⛔ 28.1 Runs 001 and 002 are VOID — and why that is worth a section

Both are **repeats of an already-exposed fill**. The first attempt at each hit §27.25's discard bug: a
successful run whose winner had lost its spectrum was reported as *"Capture failed — no frames were
delivered by the camera"*, so the jar was re-measured after banking light dose.

⇒ ⛔ **the σ_fill of 0.696 first computed from them is withdrawn**: it is fill scatter plus two unknown
doses. ⚠ And nothing in the record said so — a `MonitorRecord` has no field for *this fill had already
been in the beam* (§27.25's M4, still owed). The lesson is not the arithmetic, it is that **an artifact
that cannot say how it was obtained will eventually be believed.**

### ⭐ 28.2 The five that count

| run | material | treatment | branch | Q% | clearing | rows |
|---|---|---|---|---|---|---|
| **003** | dilution of 003, first 4 ml | used, warmed | arrived-clear | **14.246** | 105 s | 7 |
| **004** | *same dilution*, other 4 ml | kept DARK, unwarmed, 3 min bath | vertex | **14.156** | 208 s | 13 |
| **005** | dilution X, first 4 ml (**R**) | bath | arrived-clear | **14.173** | 105 s | 7 |
| **006** | **R again**, 60 s in the frog to re-muddy | bath | vertex | **13.972** | 314 s | 20 |
| **007** | dilution X, other 4 ml (**S**) | shaken again, bath | vertex | **13.499** | 207 s | 13 |

⚠ "Other 4 ml" was in fact ~3.5 ml (Edwin) — the second half of an 8 ml / 2-capillary dilution.

### ⭐⭐ 28.3 THE RESULT THAT JUSTIFIES THE WHOLE SPEC — reading early is the dominant error

| run | Q% had it been read at ~105 s | Q% the gate returned | difference |
|---|---|---|---|
| **006** | **15.005** | **13.990** | **−1.015** |
| 007 | 13.583 | 13.502 | −0.081 |
| 004 | 14.230 | 14.185 | −0.046 |

⭐⭐ **§1's claim, measured on the bench for the first time.** A muddy fill read at a fixed time is a full
unit high — and 006's `A_valley` fell **92 %** (1.067 → 0.084) over 314 s while that happened. ⇒ the
gate is not a refinement of the 15-minute rule; on this fill it is the difference between 15.0 and 14.0.

⭐ **AND θ = 0.005 DID NOT STOP TOO EARLY** (§27.26's open worry). In all three vertex runs the answer
**equals the minimum over every row**, and the rows after it are flat or already rising:

```
004   14.157  14.170  14.159  14.185      answer 14.156
006   13.986  13.987  13.972  13.990      answer 13.972
007   13.511  13.500  13.501  13.502      answer 13.499
```

⇒ the curves had bottomed out and the photodamage ramp is just beginning. The vertex guard absorbed the
early gate exactly as the jar-B replay predicted.

### ⚠ 28.4 σ_fill — two split-half pairs, and they disagree by 7×

| pair | same dilution, two halves | Δ | σ = \|Δ\|/√2 |
|---|---|---|---|
| 003 / 004 | used+warmed vs dark+unwarmed | 0.091 | ⭐ **0.064** |
| 005 / 007 | first 4 ml (R) vs other 4 ml (S) | 0.674 | **0.477** |

Pooled over the two pairs: **σ ≈ 0.34**. ⚠ Two differences, ~2 df — a magnitude, not a value.

⭐⭐ **003/004 LANDS ON THE INSTRUMENT FLOOR.** 0.064 against §16.36.6's no-re-seat floor of **0.063** —
two different halves, two different thermal histories, one measured warm and used and the other kept in
the dark and unwarmed, and they agree to within the instrument's own noise. ⇒ **when the two halves match,
the instrument is not the limit.** That is the most encouraging number this project has produced.

### ⛔ 28.5 The R/S gap — what it is NOT, and the confound that stops it being named

The 005/007 pair differs by 0.674, and R measured properly (006) against S (007) still differs by **0.473**.
Two candidate explanations were offered and **both are ruled out by the data**:

- ⛔ **NOT the 3.5 ml.** `Q%` is scale-invariant by construction, so a smaller aliquot of the same liquid
  must read the same. Measured: scaling S to match R's Soret reproduces `A_Q` to +1.6 % but leaves the
  **valley off by +9.7 %** — a SHAPE difference, which no path length or fill volume can produce.
- ⛔ **NOT residual turbidity from the extra shake.** See §28.6: the sign is wrong.

⚠ **AND THERE IS NO CLEAN R-vs-S COMPARISON IN THIS SET**, which is the honest reason the gap cannot be
attributed: **005** is R but read early; **006** is R but *after a cold shock in the frog*; **007** is S
after a shake. "R vs S" is really "R-after-freezing vs S-after-shaking".
⚠ Counter-evidence against treatment being the driver: 003 and 004 had *very* different histories and
agreed to 0.091.

⇒ **THE NEXT EXPERIMENT IS NARROW: R and S again under IDENTICAL treatment** — same shake, same bath, both
run to the gate, neither frozen. Gap persists ⇒ the halves differ materially. Gap collapses toward 0.06 ⇒
handling, and the 003/004 floor is the truth.

### ⭐ 28.6 THE TURBIDITY LINE — a standing check, free from every record

Within one clearing fill, `Q%` and the turbidity proxy `valley/Soret` fall **together**, at a roughly
constant rate:

| run | valley/Soret | Q% | slope d`Q%`/d(v/S) |
|---|---|---|---|
| 006 | 0.529 → 0.090 | 21.21 → 13.99 | **+16.4** |
| 007 | 0.111 → 0.097 | 13.78 → 13.50 | **+18.8** |
| 004 | 0.095 → 0.079 | 14.31 → 14.19 | +7.5 |

⇒ **when two readings disagree, ask first whether their difference lies on this line.** Multiply the
difference in `valley/Soret` by ~16 and compare with the observed `Q%` gap.

Applied to R vs S: Δ(v/S) = **+0.0085** predicts **+0.14** — S should read *higher*. It reads **0.473
lower**, an effective slope of **−56**: wrong sign, and three times too steep. ⇒ clearing state is
eliminated in one line of arithmetic, and the search moves on.

⚠ **IT IS NOT A CORRECTION FACTOR.** The slope spans 7.5–18.8 across three runs, so it judges whether a
difference is *plausibly* a clearing difference — sign and order of magnitude — and must never be used to
adjust a reading. ⚠ Three runs, one oil. ⭐ Everything it needs (`valley`, `soret`, `qPercent` per decision
row) is already in every embedded record, so it costs nothing to apply to any future pair.

### ⭐ 28.7 Two further findings, recorded

- ⭐ **No net photodamage at these durations.** R was in the beam ~2 min for 005, was re-muddied, and spent
  5+ min more in 006 — and read **0.20 LOWER**, not higher. Over minutes the clearing term dominates the
  browning term; §16.36's browning was measured over 72-minute arcs. ⛔ This does not retire the dose
  concern, it bounds it.
- ⚠ **005 sits ON the branch boundary.** At 110 s its `A_valley` had fallen **0.0083** against the 0.010
  materiality line — a hair below, so it was called *arrived-clear* and stopped. 004 and 007 had already
  crossed it at the same moment (0.0113, 0.0105) and were correctly routed to the vertex; 003 genuinely
  was clear (total fall 0.0023). ⇒ the classifier is working, and 005 is the case that shows where its
  edge is.

### ⚠ 28.8 What series F does NOT establish

- ⛔ **It does not exercise §27.25's M1 fix.** All three vertex winners sat 1–3 decision rows back
  (17–51 s) — inside the OLD five-row window — so these runs would have completed before the fix as well.
  M1 is right (the boundary was measured directly, §27.25) but is **still unexercised**. ⇒ the test is an
  **unwarmed muddy fill**: the longest clearing phase puts the `Q%` minimum furthest from the gate.
  ⚠ Watch `capsHit` — §16.36 saw ~17 min unwarmed against a 25-minute cap — and note it doubles as
  §17/C1's field datapoint, the case with no water bath where the two-minute claim does not hold.
- ⛔ **It is not σ_fill for the decision table.** Two pairs on one oil; §16.11.11's series E design (6
  separate fills of one stock) is what feeds §16.13's 0.307 boundary, and that is still owed.

### ⭐⭐ 28.9 WHAT THE PROTOCOL BOUGHT — measured against the archive, and what it unblocks

⭐ Edwin, 2026-08-18: *"we at least have shown that there is not such flicker in the metric values as in
previous runs of our archive … so the chance lives that even a correlation could be found with a jury
panel's judgment."* ⇒ measured, and the comparison is lopsided in the protocol's favour.

| | n | range | sd |
|---|---|---|---|
| Steirerkraft half-strength — 6 runs of **one fill** (§4.1) | 6 | 3.30 | 1.271 |
| Steirerkraft aged 24 h — 3 runs of one fill | 3 | 3.37 | 1.704 |
| Spar Steirisches g.g.A. — 3 runs of one fill | 3 | 0.75 | 0.379 |
| **pooled archive WITHIN-FILL** | | | **1.255** |
| ⭐ **series F — five SEPARATE preparations** | 5 | 0.66 | **0.276** |

⭐⭐ **4.5× tighter — and not like for like in the archive's favour.** Those archive numbers are repeats of
the *same jar*, which is the easiest thing an instrument is ever asked to do; series F's includes fresh
dilutions, fresh capillaries and fresh fills. ⇒ **the archive wobbled more re-measuring one jar than the
new protocol wobbles across five separate preparations.**
⭐ And it is not luck: §16.36 diagnosed that spread as a fill clearing and browning *while being
re-measured*. Reading each fill once, at a defined moment, is precisely what removes it — this is the first
direct measurement of what §1 promised.

#### ⭐ Why that opens the ground-truth question (§5's last row)

Measurement noise attenuates any correlation before it can be observed: `r_observed = r_true · √reliability`
with `reliability = σ²_between / (σ²_between + σ²_error)`. Against the between-oil signal of **1.167**
(`SPEC_v_metric_integration.md` V0):

| measurement noise | reliability | attenuation | a true `r = 0.90` would show as |
|---|---|---|---|
| archive, 1.255 | 0.464 | 0.681 | **0.61** |
| ⭐ **series F, 0.276** | **0.947** | **0.973** | **0.88** |

⛔ **Under the old protocol the instrument discarded a third of any correlation before the panel sat down** —
a genuinely strong relationship would have read as mediocre and a moderate one as noise, and nobody could
have told that from the result. ⭐ At today's scatter the instrument is **essentially transparent: it costs
3 %.**
⇒ ⭐⭐ **the instrument is no longer the reason a panel correlation would fail.** That is what §5's
"labels compared against a measurement that moves" row was waiting for.

#### ⚠ Three caveats, so the claim is not overspent

1. ⚠ **0.276 is five fills of one oil in one evening.** It becomes a general claim when the brown series
   (§16.11.11) reproduces it, not before.
2. ⚠ **Today's 13.4–14.5 spread is NOISE, not signal** — all seven runs are Lugitsch A. A panel study needs
   oils *spanning* the class, and the 1.167 between-oil figure above still comes from the OLD protocol; it
   may itself look different measured properly.
3. ⛔ **The panel attenuates too, and usually more.** Sensory panels typically reach a reliability of
   0.6–0.8 without replication, which would cap an observed `r` near 0.8 even with a perfect instrument.
   ⇒ the next effort belongs on **panel design** — several assessors, replicated tastings, blind and
   randomised — not on more instrument work.

⛔ **And §29 first.** An uncorrected, one-directional bias of 0.0–0.48 that scales with how fast each oil
browns is exactly the error that could **manufacture or destroy** a correlation without anyone seeing it —
faster-browning oils would carry a larger upward bias, and "browns quickly" is plausibly related to the
very property a panel would be scoring.

---

## ⭐⭐ 29 · THE READ, CORRECTED — the clear branch reports the damage it caused  *(Edwin, 2026-08-18; DESIGN, not built)*

> Figure: `docs/figures/settling_branches.svg` (generated by `diagnostics/plot_settling_branches.py`
> from the series F artifacts, so it regenerates from the reports themselves).

### ⛔⛔ 29.1 The defect

`readAs = FIRST_SETTLED_WINDOW` does **not** return the first settled window. It returns the look at which
the gate finished confirming — the **last** one — and the lamp has been bleaching the sample throughout
that confirmation. §9.6 says *"flat from the start ⇒ the first settled window IS the answer"*, and the
label says the same. Only the code disagrees.

| run | reported | its first look | bias | browning rate |
|---|---|---|---|---|
| 001 | 14.459 | 14.375 | +0.084 | +0.049 /min |
| 002 | 13.476 | 13.463 | +0.013 | +0.008 /min |
| **003** | **14.246** | **13.764** | **+0.482** | **+0.291 /min** |
| 005 | 14.173 | 14.136 | +0.037 | +0.022 /min |

⭐ **THE MECHANISM IS VISIBLE, NOT INFERRED.** Across 003's 105 s, `A_Soret` falls **2.5 %** while the
turbidity band is flat (−1.7 %, and it dips then recovers). Pigment is being destroyed. ⇒ the rise is
photodamage, not settling — §16.36's *light BROWNS, irreversibly* term, measured inside a single capture.

⛔ **IT IS ONE-DIRECTIONAL AND FILL-SPECIFIC.** Always upward, so it never averages out over repeats; and
0.291 vs 0.008 /min between two fills of the same evening — a factor of **35** — so there is no constant to
subtract afterwards. The only remedy is to report an earlier moment.
⚠ **AND IT HITS THE GOOD FILLS.** A clean sample takes this branch every time; the muddy path — where all
the design effort went — is protected. **The fill that behaves well is measured worst.**

### ⭐⭐ 29.2 The discriminator moves to the quantity being read

⛔ Today the branch is chosen by **turbidity** (`MATERIAL_FALL`: has `A_valley` fallen 0.010 below its
maximum?), i.e. the decision about *how to read `Q%`* is taken from a different quantity. Edwin's framing
names the better test: *the muddy case is a parabola with a minimum; the clear case is a monotone rise.*
⇒ **ask the curve directly — how far below the FIRST look does the `Q%` minimum sit?**

| run | A_valley fall *(the rule now)* | argmin | ⭐ depth below the first look |
|---|---|---|---|
| 003 | 0.0023 | look 0 | **0.000** |
| 005 | 0.0083 — *83 % of the threshold* | look 2 | **0.010** |
| 004 | 0.0182 | look 9 | **0.149** |
| 007 | 0.0175 | look 10 | **0.279** |
| 006 | 0.9836 | look 18 | **7.233** |

⭐ **Two clusters with a 15× gap, and the threshold falls inside it.** Single-window noise is 0.063
(§16.36.6), so **2σ ≈ 0.13** separates them — **derived, not chosen**. 005's "minimum at look 2" is 0.010
deep: noise, correctly rejected, where the turbidity rule had it at 83 % of its line.

⭐⭐ **ONE JOB EACH, which is what makes this one algorithm rather than two:**

| quantity | question | decides |
|---|---|---|
| `A_valley` (turbidity) | has the fill stopped changing? | the GATE — *when to stop looking* |
| `Q%` depth | was there a turning point? | the READ — *what to report* |

### ⭐ 29.3 The rule  *(⚠ the ORDER of the three tests is corrected in §30.3, and "the settled looks" in §30.2)*

```
gate on A_valley (unchanged)                    -> when to stop looking
then, over the settled looks:
    min is INTERIOR and deeper than 2σ          -> VERTEX read      (unchanged)
    min is at the LAST look                     -> wait one more    (unchanged)
    otherwise                                   -> the FIRST look   ⭐ the fix
```

⭐ The branch label becomes a *consequence* of the curve's shape instead of a separate decision, and
`FIRST_SETTLED_WINDOW` starts meaning what it says.

⛔ **NOT A FIT, AND THIS WAS TESTED.** A monotone rise has no turning point, and extrapolating a straight
line back to the first look's time gives **13.710** on 003 — *below* the measured 13.764 — because the
browning **accelerates** rather than running straight. An extrapolation that undershoots real data is worse
than none. ⚠ It must be a real look in any case: the SPECTRUM feeds the colour chips, the band plots and
every recomputed PDF metric, and there is no such thing as a fitted spectrum (§9.1a).

### ⚠ 29.4 What is left over — and why it argues for the shutter

The first look is centred ~5.6 s after insertion, so a little damage is already banked:

| run | still banked at the first look |
|---|---|
| 001 · 002 · 005 | 0.005 · 0.001 · 0.002 |
| **003** | **0.027** |

⇒ the fix removes **~94 %** of 003's 0.482 and essentially all of the others. ⭐ The residual is the damage
done *while the instrument waits*, and it is irreducible with the lamp on — **which is an independent
argument for §7's shutter**, arrived at from a different direction than the heated holder.

### ⭐ 29.5 The browning rate becomes a recorded diagnostic

Every run already contains it and nobody looks at it. ⇒ record `browningPerMinute` on the `MonitorRecord`
and show it in the Settling summary. ⭐ §2 asked for exactly this shape — *"zero-dose extrapolation,
reported SEPARATELY, never folded in"* — and **separate is what makes it safe**: the reported value is the
least-damaged look, while the rate says how fast this particular fill was degrading. A fill browning at
0.291 /min is a fill worth re-preparing, and today that fact is silently folded into the answer instead.

### ⚠ 29.6 What could go wrong — checked against the code

- ⛔⛔ **2σ = 0.13 IS ONLY RIGHT AT W = 60.** Window noise scales as 1/√W, and `windowFrames` is a policy
  value. A hard-coded 0.13 is the §27.25 bug in a new costume — *a constant derived at one setting, used at
  another*. ⇒ express the threshold **in units of the window's own noise**, or derive it from `W` when the
  monitor is assembled. ⛔ Do not paste the number.
- ⚠ **Selection deepens with more looks.** The minimum of *n* noisy looks sits below the first by ~0.9σ at
  n = 7 and ~1.5σ at n = 20 by chance alone. 2σ clears both, but the margin is thinner on long runs —
  worth stating so nobody lowers it to 1σ.
- ⚠ **Only full, settled looks count.** Provisional rows (ring still filling) are not decision rows and
  must stay out of the minimum hunt, or the answer can be a half-window.
- ✅ **The jar-B regression is safe**: its depth is **12.78**, a hundred times the threshold, so
  `test_clearing_evaluator` must still promote the vertex at 19.93 min with 13.2733 — an unchanged gate.
- ⚠ **It changes what four of the seven series F runs would report.** Any recomputation of archived numbers
  must say which rule produced them; ⇒ stamp the read rule's version into the record beside
  `evaluatorVersion`, exactly as §17.6 stamps the capture-decode era.

### ⭐ 29.7 Phased  *(⚠ superseded by §30.14 — R1 grew four items and R1b/R5 were added)*

```
 R1  PLUGIN   the depth discriminator + the first-look read; threshold derived from W, not pasted
              gate  005 -> first look (depth 0.010) · 004/007/006 -> vertex, unchanged
                    jar B still promotes 13.2733 at 19.93 min
 R2  SDK      browningPerMinute on the record + a row in the Settling summary
              gate  003 reports +0.291 /min beside an answer of 13.764
 R3  TESTS    the five series F runs become a replay fixture (their decision rows are in the artifacts)
              gate  each run's read reproduces the table in §29.1/§29.2 from its own record
 R4  RIG      one clear fill and one muddy fill under the new read
              gate  the clear fill's answer no longer moves with how long the gate took
```

⚠ **R1 before the brown series (§16.11.11).** A +0.48 bias is **37 % of brown's margin to `T`**, and brown
is the binding class — running the load-bearing measurement through a known one-directional bias would
spend the session and produce a number nobody can use.

---

## ⭐⭐ 30 · RUBBER-DUCK PASS ON §29 — walked against the code AND against the seven records  *(2026-08-18)*

⭐ Nothing here is estimated. Every number was recomputed from the series F reports themselves — the
`monitorRecord` embedded in each PDF's `workflow.json`, the same source `diagnostics/plot_settling_branches.py`
draws from — and every code claim names the line it is about. **Thirteen findings; four change the shape of
§29, one is a latent defect §29 merely walked past.**

### ⭐⭐ 30.1 THE FORK COLLAPSES — and `MATERIAL_FALL` must die with it

`__fireGate()` (`DevSpectralPlugin.py:184-197`) does two jobs today: it stops the gate *and* it picks the
read, promoting immediately on the clear side. §29's rule leaves it only the first job.

```
__fireGate(decisions)      -> record gateIndex, then defer to the read            (no branch decision)
__read(decisions)          -> the THREE-WAY test, called from the gate row AND from every row after it
```

⇒ `__afterGate()` and the gate's own promote become **one method with one exit table**, which is what makes
§29.2's *"one algorithm rather than two"* true in the code and not only in the prose.

⛔ **`MATERIAL_FALL = 0.010` then has no reader left** (`:67`, `:189` are its only two sites — checked across
all five repos). It must be **deleted, not retired in place**: this very file opens with a comment about two
gauge classes whose thresholds were left importable and stopped being current, and a turbidity constant
sitting in a class whose read no longer consults turbidity is the same trap.
⚠ `__hasFallenSinceMaximum()` is untouched — it is a *gate* guard (never settle at the top of a dip) and
carries no threshold.

### ⛔⛔ 30.2 "OVER THE SETTLED LOOKS" IS THE WRONG HUNT WINDOW — measured

§29.3 says the minimum is hunted *"over the settled looks"*. Taken literally that is the post-gate rows, and
it loses the vertex on every fill that has ever taken that branch:

| run | argmin at | gate fired at | the minimum is |
|---|---|---|---|
| 004 | 156.4 s | 190.6 s | **34 s BEFORE the gate** |
| 007 | 172.5 s | 189.8 s | **17 s BEFORE the gate** |
| jar B *(fixture)* | 16.66 min | 13.38 min at θ=0.005 | after — but §27.26a's early gate is why |
| 006 | 296.8 s | 279.5 s | after |

⇒ the wording must read **over every usable decision row of the run** — `row.values` truthy, `isDecisionRow`,
not `provisional` — and *"the FIRST look"* means **the run's first usable decision row**, which is what
§29.1's table already measured (t = 5.3–5.8 s on all seven runs). ⚠ This is a spec-text defect, not a code
one: `__afterGate` already hunts over all of `decisions`.

### ⭐⭐ 30.3 THE ORDER OF THE THREE TESTS MUST BE DEPTH-FIRST — or a run can end with no answer at all

§29.3 lists *interior-and-deep → vertex*, *min-at-last-look → wait*, *otherwise → first look*. Read in that
order, a **shallow** minimum that happens to sit on the newest row also waits — and if noise keeps putting it
there, the run waits to the 25-minute cap and finishes `NEVER_SETTLED` with **no value**. Today the clear
branch always answers. ⇒ the depth test must be the *first* question, so the wait is reachable only for a
curve that has already earned it:

```
depth = Q%(first usable look) − Q%(argmin)          over every usable decision row since the last reset

    depth <  2σ(W)                       ->  FIRST look        ⭐ promote now, no extra dose
    depth >= 2σ(W)  and argmin interior  ->  VERTEX            (unchanged)
    depth >= 2σ(W)  and argmin == last   ->  wait one more row (unchanged)
```

⭐ It terminates for the same reason today's clear branch does, and it saves a decision row of lamp on every
flat fill. ✅ Jar B is unharmed: its depth is **12.783** (26.0574 → 13.2744), so it enters the wait at the
early gate and still promotes 13.2733 at 19.93 min.

### ⛔⛔ 30.4 `W` IS NOT A CONSTANT — IT IS A DROPDOWN, AND THE EVALUATOR CANNOT SEE IT

§29.6 was right to forbid pasting 0.13, and the reason is stronger than it assumed. `W` is **whatever the
operator picked in the Frames combo**: `CapturePanel.__monitorFor()` passes `frames=frameCount` (`:808`) into
`createMonitor()`, which makes it `policy.windowFrames` (`DevSpectralPlugin.py:352`). The choices are
`["10", "20", "50"]` plus the plugin's declared `FRAMES = 60` (`CapturePanel.py:73,190`).

| W | 2σ = 2 · 0.063 · √(60/W) | what it does to the series F record |
|---|---|---|
| 60 *(all seven runs)* | **0.126** | the rule as measured |
| 50 *(the fallback, see below)* | 0.138 | 004 survives by 8 % |
| 20 | 0.218 | ⛔ **004 (0.149) flips to "clear"** |
| 10 | 0.309 | ⛔ **004 and 007 (0.279) both flip** |

⇒ 004 mis-branches at any **W ≤ 42**. ⛔ And the evaluator is handed `(plugin, reference, mode)` — **it is
never told the window it is judging**. So R1 is not "compute a constant differently", it is *"give
`ClearingEvaluator` the window, then derive from it"*: `createMonitor()` already builds both objects and holds
the number.
⚠ **A second window lives in the same file**: `MONITOR_WINDOW_FRAMES = 50` (`:335`) is the fallback when
`frames` is None, while the plugin declares `FRAMES = 60` (`:305`). Nothing states why they differ, and under
§29 the difference is a 10 % looser threshold on any path that forgets to pass the combo. ⇒ derive the
fallback from `FRAMES`.

### ⚠ 30.5 1/√W IS AN UPPER BOUND ON THE SHRINK — so the threshold must be CLAMPED, not scaled freely

The 0.063 of §16.36.6 is the sd of **ten whole repeats with the jar untouched** at W = 60 — it contains lamp
and AE drift that does *not* average down with more frames. Scaling it *up* for a smaller window therefore
**over-states** the noise, which raises the threshold, which pushes runs toward the clear branch — and §30.6
shows that is the expensive direction. ⇒ derive `2σ(W) = 2 · 0.063 · √(60/W)` but **clamp it at its W = 60
value of 0.126**, and record `windowFrames` and the threshold actually used on the `MonitorRecord`, so any run
can be re-judged later without guessing which number it was measured against.

### ⭐⭐ 30.6 THE ERROR IS ASYMMETRIC BY A FACTOR OF ~100 — which is what licenses a loose 2σ

| the mistake | what it costs, measured |
|---|---|
| a clearing fill read as **clear** *(false FIRST look)* | 006: **+7.233** · jar B: **+12.783** |
| a flat fill read as **a vertex** *(false VERTEX)* | 005: the vertex of its own noise sits **0.010** from its first look |

⛔ A monotone rise can never take the false-vertex path — its argmin is index 0, which is not interior (003,
002, 001 all have argmin = 0). The only candidates are genuinely flat-and-noisy curves, and there the two reads
differ by hundredths.
⭐ ⇒ **the depth threshold's job is dose, not correctness.** Getting it slightly too low costs one extra
decision row and ~0.01 units; getting it too high costs up to 12.8. That is the argument §29.6 was missing,
and it is also why §29.6's *"nobody lower it to 1σ"* should be read as *"and nobody RAISE it either"*.

### ⚠ 30.7 THE 5-SECOND CADENCE WILL MOVE THIS THRESHOLD — and it is already queued

§27.26 holds the 5 s decision row until M5. When it lands, W = 60 frames at ~3.5 fps is **~17 s of frames
stepping every 5 s ⇒ ~70 % overlap**, and a 105 s run yields ~21 looks instead of 7. Two things move at once:
more looks deepen the chance minimum (§29.6's 0.9σ → 1.5σ), while overlap makes them correlated, so the
effective count is far below 21. ⛔ Neither effect is derivable from the numbers here. ⇒ add to the held item:
*the depth threshold is re-measured on real overlapping rows before the 5 s cadence ships* — it must not be
carried across a cadence change, which is precisely the §27.25 mistake in its third costume.

### ⛔ 30.8 RE-CLOUDING MUST RESET THE HUNT WINDOW

TEST B (`__isReclouding`) resets the gate and sets `__reclouded`, which today only colours the coach line. Under
§29 the argmin is hunted over the whole run — so a fill that clouded, was warmed and cleared again can have its
**first look taken from before the cloud event**. ⇒ the evaluator keeps a `huntFrom` index, set to the current
row whenever TEST B fires, and both the depth and the "first look" are measured from there.

⭐⭐ **AND THE FAILURE IS NOT THE ONE THIS SECTION FIRST NAMED — measured 2026-08-18, after the build.** The
draft said the read would take *"the most turbid moment of the run"*. It does not: a jar leaves the 52 °C bath
CLEAR and clouds on the way in, so the pre-cloud look is the **lowest** point of the curve, not the highest.
Replaying the re-clouding fixture with the reset disabled reports **13.40 at t = 0.6 min, depth 0.000, branch
"arrived clear"** — a look taken *before the jar clouded at all*, labelled as a curve that never turned. With
the reset it reads the vertex: **13.42 at 6.6 min, depth 2.180**.
⛔ On this curve the two VALUES differ by 0.02; the CLAIM differs completely, and so does the spectrum that
travels with it — a window six minutes and one phase change away from the one reported. A fill that settles
below its pre-cloud value would separate the numbers too.
⚠ Still untested on real glass — none of the seven series F runs re-clouded.

### ⭐ 30.9 THE FIRST-LOOK READ DEPENDS ON §27.25's RETENTION FIX — say so where it can be broken

The promoted row's spectrum is the answer's spectrum (`MonitorEngine.py:251`). On the clear branch that row is
now the **oldest** decision row of the run, i.e. the single most prunable object in the engine. It survives only
because §27.25/M1 sized retention as `maxSeconds` (`__retentionSeconds`, `:216`). ⇒ a comment at the read, and a
line in §27.25: **shortening retention no longer costs the vertex branch its spectrum — it costs the CLEAR
branch its spectrum, on every run.** That failure mode already has a measured price: the "Capture failed — no
frames were delivered" dialog that cost two measurements on 2026-08-17.

### ⭐ 30.10 `clearingSeconds` AND THE ANSWER'S `t` NOW DIVERGE BY DESIGN

`__clearingSeconds` is stamped at the **gate** row (`:255`), the answer carries its own `t`. On the clear branch
those are now ~100 s apart and mean different things:

| run | answer `t` *(the read)* | `clearingSeconds` *(the gate)* |
|---|---|---|
| 001 | 5.6 s | 107.9 s |
| 003 | 5.6 s | 105.1 s |
| 005 | 5.5 s | 105.0 s |

⇒ the Settling summary prints **both**, labelled *"read at"* and *"gate confirmed at"*. ⛔ §2.4 logs
`clearingSeconds` as a σ_fill component; one of these silently standing in for the other is how a σ_fill number
gets built on the wrong quantity.

### ⭐ 30.11 `browningPerMinute` — the definition, pinned to the form that reproduces §29.1

Two candidates, both computed over *the read row → the last usable row*:

| run | two-point Δ/Δt | least-squares slope | §29.1's table |
|---|---|---|---|
| 001 | **0.049** | 0.041 | 0.049 |
| 002 | **0.008** | 0.008 | 0.008 |
| 003 | **0.291** | 0.278 | 0.291 |
| 005 | **0.022** | 0.026 | 0.022 |

⇒ **the two-point form is the shipped one**, and not merely because it matches: it is the damage *actually*
banked between the read and the end of the run, whereas a fit is a model of it. ⭐ It is defined on **both**
branches (004: +0.032, 006: +0.061, 007: +0.004 after their vertex) — so it also says what the muddy branch's
waiting cost. ⚠ But only **2–4 rows** follow the read there (004: 4, 006: 2, 007: 3) ⇒ **record it, never gate
on it**, and the summary should show the row count beside it.

### ⚠ 30.12 THE STAMPS AND THE TESTS THAT PIN THE OLD RULE

- ⭐ `ClearingEvaluator.version = "clearing-1.0"` → **`"clearing-2.0"`**. It already travels as
  `evaluatorVersion` (`createMonitor`, `:357`), and all seven series F records carry `1.0` — so §29.6's
  "say which rule produced them" needs no new field, only the bump.
- ⚠ `MonitorOutcome.SETTLED_IMMEDIATE`'s own comment says *"the fill arrived clear"* (`MonitorOutcome.py:11`),
  and the plugin's glossary repeats it (`DevSpectralPlugin.py:489,509`). Under the new rule it means *"no
  turning point deeper than noise"* — and it can now fire minutes in. ⛔ Do **not** rename the enum: it is
  persisted in every saved record. Re-word both texts instead.
- ⚠ `tests/test_clearing_evaluator.py:109` justifies its branch assertion as *"A_valley fell 0.92 — far
  beyond the 0.010 materiality"*. That sentence stops being true; the same assertion must be re-justified on
  **depth 12.783**. `:174-177` pins the arrived-clear path and needs the depth case beside it.
  `test_monitor_engine.py` drives a stub evaluator and is untouched; `test_settling_views.py:77` asserts a
  fixture string, also untouched.

### ⛔ 30.13 A LATENT DEFECT FOUND ON THE WAY — retention smaller than the window kills every row

`MONITOR_RETENTION_FRAMES = 60` is a **constant** while `windowFrames` comes from the dropdown
(`DevSpectralPlugin.py:336,352-353`). If a plugin ever declares `FRAMES > 60` — and the combo's own comment
cites *"the dev bench's 150"* — then `FrameRing.window()` can only ever return 60 frames, the engine's
`len(window) >= minWindowFrames` never holds, **no row is ever emitted**, and the run burns the full 25-minute
cap to finish `NEVER_SETTLED` with an empty trajectory. ⇒ retention must be derived from the window in force
(`frames + max(5, frames // 5)`, the FrameRing default), not pinned to 60. ⚠ Harmless today (60 is the largest
selectable), which is exactly why it would be found the hard way.

### ⭐ 30.14 THE PHASING, REVISED  *(✅ R0–R3 BUILT — see §30.16; ⚠ only R4 rig + R5 held remain)*

```
 R1  PLUGIN   the fork collapses into one read (30.1) · MATERIAL_FALL deleted
              hunt window = every usable row since the last re-clouding reset (30.2, 30.8)
              depth-first ordering (30.3)
              the evaluator is HANDED W; 2sigma(W) derived and clamped at 0.126 (30.4, 30.5)
              gate  005 -> first look (depth 0.010) · 004/007/006 -> vertex, unchanged
                    jar B still promotes 13.2733 at 19.93 min (depth 12.783)
 R1b PLUGIN   retention derived from the window in force (30.13) — independent, ship it with R1
 R2  SDK      browningPerMinute (two-point, 30.11) + windowFrames + the threshold used, on the record
              a "read at" / "gate confirmed at" pair in the Settling summary (30.10)
              version -> clearing-2.0; SETTLED_IMMEDIATE re-worded, NOT renamed (30.12)
 R3  TESTS    the five series F runs become a replay fixture, extracted from the PDFs to a JSON in tests/
              (they live under `spectracs-references/tmp/2026ß817LigitschA/` — a hand-typed path with a
               typo in it, so the fixture must be extracted, not read from there at test time)
              gate  each run's read reproduces §29.1/§29.2 · the four clear runs move by
                    -0.084 / -0.013 / -0.482 / -0.037 and the three vertex runs do not move at all
 R4  RIG      one clear fill and one muddy fill under the new read
              gate  the clear fill's answer no longer moves with how long the gate took
 R5  HELD     re-measure the depth threshold on overlapping rows BEFORE the 5 s cadence ships (30.7)
```

### ✅ 30.15 THE ONE OPEN QUESTION — DECIDED: (a) CLAMP AND RECORD  *(Edwin, 2026-08-18)*

At **W = 10 or 20** the depth rule runs outside the range anything was measured in, and §30.5's clamp keeps it
*safe* but not *honest* — a 0.126 threshold at W = 10 will branch pure noise to the vertex. Two ways to end it:

- **(a) clamp and record** — always monitor, note "W below the validated range" on the record and in the coach
  line. Nothing is ever refused; the number carries its own caveat.
- **(b) decline below a validated W** — `createMonitor()` returns None under ~40 frames, the host falls back to
  today's plain burst, and the operator is told the settling read needs more frames.

⭐⭐ **(a) IS THE DECISION.** It never removes a capability, and — the load-bearing half — it never lets the
threshold drift in the **catastrophic** direction: over-stating the noise is what puts a still-clearing fill on
the clear branch, and that error costs +7.233 (006) or +12.783 (jar B) against the ~0.01 a false vertex costs.
⇒ derive `2σ(W)`, **clamp at 0.126**, stamp `windowFrames` and the threshold used on the record, and say in the
coach line when `W` is below the only window anything was ever measured at.
⚠ The residual is stated rather than hidden: at W = 10 the clamp is *safe* but not *honest* — the threshold is
then tighter than the true window noise, so a flat noisy curve will sometimes take the vertex branch. That
costs one decision row and hundredths of a unit, i.e. the cheap error by ~100x.
⭐ (b) remains a three-line guard in `createMonitor()` if a validated-W floor is ever wanted; the clamp does not
have to be undone first.

### ✅⭐⭐ 30.16 AS BUILT — R1b · R1 · R2 · R3, 2026-08-18  *(445 tests green; only R4/R5 remain)*

| | |
|---|---|
| **R1b** | `MONITOR_RETENTION_FRAMES` deleted; `MONITOR_WINDOW_FRAMES = FRAMES` (the two windows in one file now agree, §30.4); `createMonitor()` passes `retentionFrames=None` so `FrameRing` sizes itself. ⭐ **MEASURED, not reasoned**: at `FRAMES=150` the old shape emits **0** decision rows in 305 frames, the new one **2** |
| **R1.1** | `ClearingEvaluator(…, windowFrames=)` + `depthThresholdFor(W)` = `2 × 0.063 × √(60/W)`, **clamped at 0.126**. W 150 → 0.080 · 60 → 0.126 · 20 → 0.126 (clamped, not 0.218) · 10 → 0.126 |
| **R1.2** | `MATERIAL_FALL` **deleted**; `__fireGate()` gates only; one `__read()`; one `__depthOf()` both callers share |
| **R1.3** | TEST B sets `__huntFrom` — the re-clouding test now asserts the read cannot reach back across the cloud |
| **R1.4** | depth-first ordering, exactly as §30.3 |
| **R1.5** | the K4c wait says why; the coach line names a `W` below the validated 60 |
| **R2.1** | `MonitorDecision(diagnostics=…)` merged into `answer` by the engine — ⭐ the only core change, ~10 lines, and `grep qPercent` in `plugin_sdk/acquisition` still returns **comments only** |
| **R2.2** | `browningPerMinute` (two-point) · `rowsAfterRead` · `depth` · `depthThreshold` · `windowFrames` · `readRule` |
| **R2.3** | header `read at` / `gate at`; "Clearing time" → **"Gate confirmed at"**; new **Browning** and **Curve depth** rows; the gate marker now also on the **Q%** panel |
| **R2.4** | `version = "clearing-2.0"`; `SETTLED_IMMEDIATE` re-worded in all three places, ⛔ not renamed |
| **R2.5** | a **second** representative frame (the first), chosen by proximity to `answer.frameIndex` |
| **R3.1/3.3** | `tests/data/series_f_records.json` + `tests/test_series_f_replay.py` — 15 tests, all seven runs |
| **R3.2** | `test_clearing_evaluator` re-justified on **depth 12.783**; three new tests (clamp · shallow-interior · the wait) |

#### ⛔⛔ THE ARCHIVE REFUTED THE FIRST CUT — and this is what R3 was for

The first implementation read **at** the gate row on *both* branches. It looked like free dose: jar B then
answered at 19.93 min at either θ, and `test_the_shipped_theta_saves_dose_and_reads_the_SAME_value` went red
saying so. ⭐ Replaying **run 006** showed the price: its gate fires at 279.5 s, and at that instant the
deepest look so far (262.6 s) already had a row on its far side — a legitimate-looking interior minimum. The
**true** minimum arrives at 296.8 s, **0.012 lower**. ⇒ reading at the gate settles on a local dip while the
fill is still descending.

⇒ **the vertex branch still waits one decision row (§14.4), unchanged**, exactly as §29.3 and §30.14 promised
and as the first cut quietly was not. ⭐ The clear branch is different in kind and reads immediately: its
answer is the *first* look, and no further waiting can improve a row already captured.
⚠ **Neither θ test was "fixed" by moving it** — one was restored to its original assertions because it had
been right, and both still pin the θ they are about.

#### ⭐ What the seven runs now report *(replayed through the shipped evaluator)*

| run | branch | reads | moves by | browning |
|---|---|---|---|---|
| 001 · 002 · 003 · 005 | arrived-clear | the **first look** | −0.084 · −0.013 · **−0.482** · −0.037 | 0.0495 · 0.0077 · **0.2909** · 0.0222 /min |
| 004 · 006 · 007 | was-clearing | the vertex, **bit-identical** | 0.000 | 0.0324 · 0.0614 · 0.0042 /min |

#### ⭐ 30.17 THE RE-CLOUDING BRANCH, MEASURED BOTH WAYS  *(2026-08-18)*

Replaying the re-clouding fixture with `huntFrom` pinned at 0 — i.e. the algorithm without §30.8 — is what
established which failure the reset actually prevents, and it is not the one §30.8 first named:

| | huntFrom | branch | reads | depth |
|---|---|---|---|---|
| **shipped** | 5 | was-clearing | **13.42** at 6.6 min | 2.180 |
| **reset disabled** | 0 | ⛔ arrived-clear | **13.40** at **0.6 min** | 0.000 |

⛔ Without it the run reports a look taken *before the jar clouded at all* and declares that the curve never
turned. ⭐ The jar leaves a 52 °C bath CLEAR and clouds on the way in, so the pre-cloud look is the **lowest**
point of the curve — which is exactly why it slips through as a plausible answer rather than an obvious one.
⚠ Three limits, stated so nobody assumes more coverage than exists: TEST B needs **5 decision rows** (~85 s at
W = 60), so a faster cloud event is invisible to it; an event inside the first window is invisible entirely;
and after a reset the depth is inflated by the cloud recovery itself (the span's first look sits on the
falling side of the dip), so it must not be read as "how much the sample settled".
⚠ `__hasFallenSinceMaximum` remains scoped to ALL rows rather than to the hunt window. It passes trivially
after a reset, so nothing is wrong today — but it is the one place where the two scopes disagree.

#### ⚠ TWO THINGS FOUND AND NOT FIXED

- ⛔ **The dev plugin does not pass `lintSelfContained`** — it imports three sibling gauge views
  (`RoastPedestalGaugeView`, `RoastFar620GaugeView`, `RoastQPercentGaugeView`). **Pre-existing and
  unchanged by this work** (verified against `HEAD`); it is injected transiently rather than published, so
  nothing is broken today — but it could not be published as-is.
- ⚠ **R2.5 cannot make the photo the winning window's own.** The engine promotes a REDUCED spectrum and the
  raw frames behind it are gone (§9.1a). Keeping two frames only stops the picture coming from the opposite
  end of the run from the spectrum beside it.

<!--PAGEBREAK-->

## ⭐⭐ 31 · TEST C — THE DEGRADING FILL — a monotone rise that neither A nor B can see  *(Edwin's run 001 of 2026-08-19; DESIGN, not built)*

> *"i am currently measuring an old sample from yesterday where the turbidity seems to rise and rise and
> rise. so the settlement algorithm takes long. think that is okay?"*

⭐ **The answer it produced was right. The way it got there was not, and it got out by luck.**

### ⭐ 31.1 THE EVIDENCE — `20260819/001`, a day-old fill, 43 rows

```
outcome SETTLED_IMMEDIATE | answer Q% = 13.585 at t = 6.32 s | branch arrived-clear
readAs FIRST_SETTLED_WINDOW | depth 0.111 vs threshold 0.126 | browningPerMinute 0.048
clearingSeconds 758.1 | rowsAfterRead 43 | W = 60
```

| | row 0 (6.3 s) | row 42 (758.1 s) | |
|---|---|---|---|
| `A_valley` | 0.0463 | 0.0610 | ⛔ **+32 %, monotone — it never once fell** |
| `A_Soret` | 0.6798 | 0.6551 | −3.6 %, monotone |
| `Q%` | 13.585 | 14.185 | dips to 13.474 at row 7, then climbs |

⭐ **Nothing settled at any point in 12.6 minutes.** This is what a day-old dilution is expected to do —
Ostwald ripening and coalescence coarsening the droplets (`DOC_sample_physics.md` §4.4,
`SPEC_capture_quality.md` §16.12.2). ⚠ The mechanism is inferred from the shape and the sample's age; it was
not independently confirmed on this fill.

### ⛔⛔ 31.2 WHY IT TOOK 12.6 MINUTES — and why it nearly took 25 with no answer at all

⛔ **It was not the rate test.** The valley climbs at **0.0012 /min**, comfortably under `θ = 0.005`, so
**TEST A called the fill flat from the third row onward** and `__consecutiveFlat` was satisfied almost
immediately. What blocked the gate for forty-two consecutive rows was this:

```python
def __hasFallenSinceMaximum(self, decisions):        # §14.5, "never settle at the TOP of a re-clouding dip"
    maximumIndex = valleys.index(max(valleys))
    return maximumIndex < len(valleys) - 1
```

⭐⭐ **On a monotonically rising valley the maximum IS always the newest row**, so this returned `False`
every time. The gate fired at row 42 — when the valley ticked **0.0610 → 0.0609**. ⛔ **A noise tick of
0.0001 released the run.**

⛔ **Had the rise continued cleanly to `maxSeconds`, the gate would have been blocked to the cap and the run
would have ended `NEVER_SETTLED` with NO VALUE** — while a perfectly good first look sat in the trajectory
from 6.3 seconds. ⚠ That is the §30.3 failure mode ("a run can end with no answer at all") arriving through
a door §30.3 did not close.

⚠ **And the guard stalls SILENTLY.** Forty-two rows of blocked gate produced no note, no diagnostic and no
operator-facing word. The record of run 001 does not say why it took 12.6 minutes; it had to be reconstructed
from the trace.

### ⛔ 31.3 WHY TEST B IS THE WRONG TEST FOR IT — the mirror image, not another instance

The first instinct is *"the valley is rising, that is TEST B"*. ⛔ **It is the opposite case, and merging them
would be a defect.** TEST B (§14.5, `__isReclouding`) requires

```python
return slope > self.THETA_PER_MINUTE and slope > 2.0 * standardError
#            ^ MAGNITUDE  0.005/min       ^ SIGNIFICANCE
```

⭐⭐ **Only the magnitude term separates the two cases.** Measured on the 001 trace, the significance half
passes overwhelmingly and everywhere:

| baseline | slope /min | std error | **slope / stdErr** | `> θ`? |
|---|---|---|---|---|
| 5 rows @ row 8 | 0.00094 | 0.000099 | **9.5** | ⛔ no |
| 5 rows @ row 30 | 0.00140 | 0.000036 | **38.6** | ⛔ no |
| 5 rows @ row 41 | 0.00104 | 0.000064 | **16.1** | ⛔ no |
| **whole run, 43 rows** | **0.00122** | 0.0000071 | **171.5** | ⛔ no |

⇒ **θ is a magnitude threshold: right for flatness, wrong for a trend.** ⚠ Note the pre-§27.26 value of
0.0017 would have missed it too — this is not an artefact of the jar-B raise.

⛔⛔ **AND LOWERING θ WOULD BE ACTIVELY HARMFUL, WHICH IS THE REAL POINT.** TEST B does not merely reset the
gate; per §30.8 it resets the hunt window:

```python
self.__huntFrom = len(decisions) - 1     # everything before this row belongs to a cloudier fill
```

⭐ That is correct for a re-cloud — the fill re-clouded and will clear again, so the pre-event rows describe a
different fill. ⛔ **It is exactly wrong for a ripening fill, where the earliest row is the LEAST contaminated
one and the answer.** A θ low enough to catch 001 would have fired TEST B on nearly every row, marched
`huntFrom` forward behind the degradation, discarded the best data at each step, restarted `clearingSeconds`
each time, and run to the 25-minute cap — then reported the **most** degraded look of the run, or nothing.

| | ⭐ **TEST B — re-clouding** | ⭐⭐ **TEST C — degrading fill** |
|---|---|---|
| rate | fast, above θ | slow creep, ≪ θ, but hugely significant |
| shape | a step — an **event** with a start | monotone **from row 0** |
| physics | crossing the cloud point on the way in (§14.5) | ripening / coalescence (`DOC_sample_physics` §4.4) |
| reversible | ⭐ **yes** — the lamp re-warms it and it clears | ⛔ **no** — droplets do not un-coarsen |
| the future | it will get better | it will only get worse |
| earlier rows | ⛔ invalid — discard (`huntFrom`) | ⭐ **the best data — keep** |
| correct action | **wait**, reset the clock | ⭐⭐ **stop**, read the first look, say so |

### ⭐⭐ 31.4 THE RULE

```
   ⭐ TEST C — DEGRADING FILL   (LONG baseline, SIGNED, significance-only — no magnitude term)

        least-squares slope of A_valley over the last m_degrade = 10 decision rows
             slope > k_sig * its own standard error,   k_sig = 4
        AND  the rise across that baseline >= f_floor * A_valley(now),  f_floor = 1 %
        AND  TEST B did not fire on this row
        for k_degrade = 2 consecutive decision rows

        ->  DEGRADING: stop the run, read NOW, and tell the operator the fill is going backwards
```

⭐ **Three terms, three different jobs, and none of them is θ.**

- **`slope > 4 * stdErr` is the detector.** It is the only clause with evidence behind it: on 001 it holds at
  9–39 on every window and 171 over the run, while on a flat fill the slope is zero-mean noise and the test
  is a 4σ one-sided event per row, squared by `k_degrade = 2`.
- **`rise ≥ 1 % of A_valley` is not a second significance test — it is a RELEVANCE test.** With enough rows,
  an arbitrarily small real drift becomes significant; this clause says *do not end a run over a rise that
  does not matter*. ⚠ **Reasoned, not measured.** On 001 the rise across ten rows is **6.0 %** — six times
  the floor — so the rule is not sitting on this number; it is a backstop.
- **`m = 10` rather than TEST B's 5** buys separation from TEST B *and* an honest lever arm. ⚠ It costs the
  first ~3 minutes: TEST C cannot fire before ten decision rows exist.

⭐ **Simulated against the 001 trace** (the rule replayed row by row):

| `m` | fires at row | **t** | slope/stdErr there | rise | vs the 12.63 min it actually took |
|---|---|---|---|---|---|
| 5 | 5 | 1.57 min | 7.3 | 2.9 % | 8.0× less lamp — ⛔ but shares TEST B's baseline |
| 8 | 8 | 2.46 min | 16.0 | 4.3 % | 5.1× less |
| ⭐ **10** | **10** | **3.06 min** | **21.2** | **6.0 %** | ⭐ **4.1× less lamp, at 21σ** |

⇒ **`m = 10` is the recommendation**: it ends run 001 at 3.06 minutes instead of 12.63 with a 21σ margin —
not a knife-edge — and it cannot be confused with a re-cloud, which fires at 5 rows and a 4× larger rate.

### ⛔⛔ 31.5 WHAT IT READS — and the ONE place the vertex must be refused

⭐ **TEST C does not invent its own read.** It stops the looking and hands the curve to `__read` (§30.1: one
read, asked repeatedly) — with a single exception, and the exception is load-bearing:

```
   if  argmin(A_valley) == huntFrom     # the turbidity NEVER fell: the fill never cleared at all
   ->  the vertex branch is REFUSED. The FIRST look is the answer, whatever the depth says.
```

⛔⛔ **Why.** On 001 the `Q%` curve *does* have a turning point — 13.585 → 13.474 over seven rows, then up to
14.185 — and `depth = 0.111` against `threshold = 0.126` is only a **12 % margin**. Had it cleared that
threshold, `__read` would have taken the **vertex at row 7 and called it the settled value.** ⛔ On a fill
whose turbidity never fell, that turning point is not a settling minimum: it is the **crossover where rising
turbidity and falling Soret happen to balance** — the point where two contaminations cancel, not the point
where either is smallest. ⭐ It is meaningless, and it would have been reported with a straight face.

⚠ **The other shape is real and must keep the vertex.** A fill that genuinely clears, reaches its minimum,
and *then* begins to ripen has a true settling vertex; there TEST C's only job is to stop the run early and
flag the sample. The `argmin(A_valley)` test is what separates the two, and it is the same quantity §29.2
moved *away* from for the branch decision — ⭐ used here for a different question ("did it ever clear at
all?"), which is the one question turbidity is still the right witness for.

⚠ **The depth test's own weakness, recorded and NOT fixed here.** It compares a seven-row trend against
*single-window* noise (§30.5's σ), which understates the trend's significance. On 001 it gave the right
answer for the wrong reason. ⛔ Do not lower `depthThreshold` before this is re-derived.

### ⭐ 31.6 WHERE IT SITS IN `decide()`

```python
if self.__gateIndex is not None:          # unchanged — §30.1
    return self.__read(decisions)

if self.__isReclouding(decisions):        # ⭐ TEST B FIRST, ALWAYS. A real re-cloud outranks a slow
    ...                                   #    trend, and it moves huntFrom, which resets C's baseline.
    self.__degradingRun = 0
elif self.__isDegrading(decisions):       # ⭐ TEST C — new
    self.__degradingRun += 1
elif self.__isFlat(decisions):            # ⭐ TEST A — unchanged
    self.__consecutiveFlat += 1
else:
    self.__consecutiveFlat = 0
    self.__degradingRun = 0

if self.__degradingRun >= self.DEGRADE_CONSECUTIVE:
    return self.__fireDegraded(decisions)             # stop + read, per §31.5
if self.__consecutiveFlat >= self.GATE_CONSECUTIVE and self.__hasFallenSinceMaximum(decisions):
    return self.__fireGate(decisions)
return MonitorDecision.carryOn(note)
```

⚠ **Ordering claims, stated so they can be checked:** (1) TEST B is evaluated first because a genuine
re-cloud must not be read as degradation — its rate is 4× larger, so on real data the two do not overlap;
(2) a TEST B reset **must** zero `__degradingRun`, because `huntFrom` has moved and the baseline TEST C was
fitting no longer describes the fill in the beam; (3) TEST C is checked before the gate so that a degrading
fill can never reach `__fireGate` and take the clearing path.

⭐ **TEST C is an `elif` of TEST A on purpose.** A row cannot be both flat and significantly rising — but
`__isFlat` uses one 70-second comparison and `__isDegrading` a ten-row fit, so both *can* be true at once,
and on 001 both were true for forty rows. ⇒ **degradation outranks flatness**, or the gate would win the race
on exactly the fill TEST C exists to catch.

### ⭐ 31.7 WHAT THE RUN SAYS ABOUT ITSELF

⭐ **A new outcome, and the enum's own comment is the argument for it:** *"an outcome without a value must
always say WHY."* Here the outcome **has** a value, and it must still say why the run ended.

```python
DEGRADING_FILL = "DEGRADING_FILL"   # the fill was coarsening, not settling — the FIRST look is the answer
...
def hasValue(self):
    return self in (SETTLED_IMMEDIATE, SETTLED_AFTER_CLEARING, COMPLETED, DEGRADING_FILL)
```

⚠ **This is an ADDITION, not a rename** — §30.12's objection to renaming `SETTLED_IMMEDIATE` (it is persisted
in every saved `MonitorRecord`) does not apply: adding a member orphans nothing. Touch points are few and
known: `MonitorOutcome.hasValue`, the outcome glossary at `DevSpectralPlugin.py:668`, the coach line, the
report header, and `test_monitor_engine` / `test_clearing_evaluator`.

⛔ **The alternative — reuse `SETTLED_IMMEDIATE` and carry the degradation in `diagnostics` — is rejected**,
because the operator would then be told *"settled"* about a fill that never settled, with the truth one level
down in a dict. ⚠ **The one open question for Edwin:** whether `branch` also gains a third value
(`"degrading"` beside `"arrived-clear"` / `"was-clearing"`). Recommendation: **no** — the read genuinely *is*
the first settled window, and `branch` is consumed by the report renderer and the settling views; the outcome
carries the news.

**Diagnostics to record** (opaque dict, §30/R2.1 — no record key, no migration):

| key | |
|---|---|
| `degradingPerMinute` | the fitted `A_valley` slope at the firing row — ⭐ the number that says *how fast the sample is dying* |
| `degradingSignificance` | `slope / stdErr` — 21.2 on 001 |
| `degradingRisePercent` | rise across the baseline as % of `A_valley` — 6.0 on 001 |
| `valleyFell` | `argmin(A_valley) > huntFrom` — ⭐ **whether the vertex was available at all** (§31.5) |
| `depth`, `depthThreshold`, `browningPerMinute` | unchanged |

**Operator-facing, per §13.** The coach line becomes `"⚠ the fill is getting cloudier, not clearer — reading
now"`, severity `WARN`, and the run ends with a verdict-level sentence the miller can act on:

> ⭐ **"This fill is degrading — the reading stands, but prepare a fresh dilution."**

⭐ That connects to a rule the archive already carries: **measure within the hour** (`SPEC_capture_quality`
§16.11, the aged-fill finding). ⇒ TEST C is the instrument finally *enforcing* a protocol rule it had only
been documenting.

### ⚠ 31.8 THE SILENT STALL IS A SEPARATE FIX — do it with C, not instead of it

⛔ `__hasFallenSinceMaximum` blocking the gate produces **no note whatsoever**. Even with TEST C in place it
can still block (a rise too slow or too small for C), and it must stop doing so mutely:

```python
"gate held — A_valley's maximum is the newest look (%d rows), so nothing has settled yet"
```

⭐ The phrase must not contain *"gate fired"*, which §14.3's acceptance test greps for.

### ⚠ 31.9 WHAT COULD GO WRONG — checked against the seven series F runs and the code

| ⚠ | |
|---|---|
| **a slow re-cloud that would have recovered** — C ends a run that TEST B would have let clear | ⭐ mitigated by `m = 10` (a cloud-and-recover episode has a falling side within ten rows, which breaks the fit) and by TEST B's priority. ⚠ **Not measured** — none of the seven series F runs re-clouded, and the re-clouding fixture is synthetic |
| **a false positive on a genuinely clear fill** | slope is zero-mean noise there; `4σ` on two consecutive rows plus a 1 % rise floor. ⛔ **must be replayed against all seven series F records before it ships** — a rule that fires on a good fill costs a measurement |
| **`huntFrom` interaction** | ⭐ TEST C must NEVER move `huntFrom`. Stated here because it is the single easiest mistake to make while implementing it beside TEST B |
| **the first frames after insertion** | ⚠ §16.36 records a real settling transient on a *fresh* fill; ten rows at ~18 s is ~3 min, well past it. At a 5-second cadence (§30.7) ten rows is **50 s**, which is not — ⛔ `m` may need re-deriving in TIME rather than in rows when the cadence changes, exactly as §14.3 did for the rate |
| **`A_Soret` divergence as a second discriminator** | ⛔ **MEASURED AND REFUTED for TEST C's regime — §31.9a, refined in §31.9b.** The coupling is real (`k = 1.49 ± 0.03` in our turbidity regime), but bleaching swamps it at any rise rate slow enough to be TEST C's business — and the break-even depends on *this fill's* bleach rate, which varies 4× and is unknowable mid-run. ⇒ ⛔ **never gate on the sign** |

### ⛔⛔ 31.9a THE `A_Soret` DIVERGENCE, MEASURED AGAINST SERIES F — the premise is TRUE and the discriminator is USELESS  *(2026-08-19, from the seven Lugitsch A records already on disk)*

§31.9 offered the sign of `ΔA_Soret` as a second discriminator: *a re-cloud adds a scattering pedestal that
lifts both bands, so divergent signs mean ripening and same signs mean re-clouding.* ⭐ **Edwin asked for it to
be checked against the last Lugitsch runs rather than left as reasoning. It was, and the answer splits in two.**

#### ⭐ THE PREMISE IS CONFIRMED — `k = 1.05`, measured almost free of any bleaching assumption

⭐⭐ **Run 006 is the instrument for this**, and it was already in the archive: its first nine rows sweep
`A_valley` from **1.0671 to 0.1424** — a **13× turbidity range** — in 2.06 minutes. Over so large a change in
so short a time, photobleaching is a rounding error, so the ratio is nearly assumption-free:

| assumed bleach rate | **k = ΔA_Soret / ΔA_valley** | bleaching's share of the Soret change |
|---|---|---|
| 0.000 /min | 1.065 | 0.0 % |
| −0.005 /min | **1.054** | 1.0 % |
| −0.010 /min | 1.043 | 2.1 % |
| −0.020 /min | 1.021 | 4.2 % |

⇒ ⭐ **`k = 1.05 ± 0.02` across the whole plausible bleach range.** Turbidity really does move both bands
together, and it moves the Soret *slightly more* — which is the right sign for a scattering pedestal, since
448–460 nm is bluer than 500–560 nm.

#### ⭐ AND IT YIELDS THE BLEACH RATE OF EVERY FILL — `b = (ΔA_Soret − k·ΔA_valley) / Δt`

| run | ΔA_valley | ΔA_Soret | Δt | **b /min** |
|---|---|---|---|---|
| 001 | −0.0013 | −0.0075 | 1.70 | −0.0036 |
| 002 | −0.0019 | −0.0075 | 1.69 | **−0.0033** ⭐ the gentlest |
| 003 | −0.0016 | −0.0210 | 1.66 | **−0.0117** ⛔ the harshest — and 003 is §29.1's −0.482 run |
| 004 | −0.0182 | −0.0415 | 3.37 | −0.0066 |
| 005 | −0.0083 | −0.0251 | 1.66 | −0.0099 |
| 006 | −0.9836 | −1.0854 | 5.14 | −0.0102 |
| 007 | −0.0175 | −0.0388 | 3.36 | −0.0061 |

⭐ **A 3.6× spread across seven fills of the same oil on one evening.** ⇒ ⛔ **`ΔA_Soret` can never be a
predictive gate on magnitude** — there is no "expected" Soret fall to compare against. Only its *sign* was ever
on offer, which is what the next paragraph kills.

#### ⛔⛔ THE DISCRIMINATOR DIES ON THE BREAK-EVEN ARITHMETIC

A rising valley lifts the Soret by `k·ΔA_valley` while the lamp removes `|b|·Δt`. The sign is diagnostic **only
when the lift wins**:

```
   k * riseRate * dt  >  |b| * dt        ⇒        riseRate  >  |b| / k
```

| bleach rate | rise rate the fill must exceed before the Soret sign means anything |
|---|---|
| −0.0033 /min (gentlest fill) | 0.0031 /min |
| −0.0066 /min (median) | **0.0063 /min** |
| −0.0117 /min (harshest fill) | 0.0111 /min |

⛔⛔ **That break-even band straddles `θ = 0.005 /min` — TEST B's own threshold.** ⇒ **the Soret sign only
becomes readable in the regime where TEST B already fires on the rate alone.** It tells you nothing you did not
already know, and it is silent everywhere TEST C operates.

⭐ **Checked on the fill itself.** `20260819/001` rose at **0.0012 /min** — **5× below the median break-even**:

```
   scattering lift over the run   k * dA_valley   =  +0.0154
   bleaching over the same run    |b| * dt        =  -0.0827   (at the median b)
                                                     ^ 5.4x larger. The Soret falls either way.
```

⇒ ⛔ **On a slow fill the Soret sign is decided by the lamp, not by the turbidity direction.** A slowly
*re-clouding* fill would show exactly the same divergence as a ripening one. **The test cannot distinguish the
two cases it was proposed to distinguish.**

#### ⚠ ONE CONSISTENCY CHECK THAT PASSES — and it is weak, so it is stated as weak

Running the coupling backwards on 001 gives an implied bleach rate of **−0.0032 /min**, which sits at the
bottom edge of series F's −0.0033…−0.0117. ⭐ With `k = 0` — no coupling at all — the implied rate would be
**−0.0020 /min, below the entire observed range.** ⇒ the data lean toward the coupling being real, ⚠ **but a
0.0012 difference against a 3.6× spread is not a decisive test**, and it is not offered as one. The `k = 1.05`
measurement above is the load-bearing evidence; this is corroboration.

#### ⛔ WHAT THIS DOES NOT SHOW

⛔ **No series F run re-clouded**, so the *positive* arm — "same signs ⇒ re-clouding" — remains **entirely
unmeasured**. What has been measured is the coupling constant that arm depends on, and it turns out to be too
small to beat the lamp at slow rates. ⇒ the arm is not merely unproven; it is **unreachable in TEST C's range**.

#### ⛔⛔ A SIDE FINDING THAT WAS RUN THE NEXT HOUR, AND CAME BACK WRONG — ⚠ **READ §31.9b BEFORE THIS BLOCK**

> ⛔ **The `n = 0.32` below is WITHDRAWN, and `k = 1.05` is superseded by `k = 1.49 ± 0.03`.** Edwin asked
> for §16.12.2B's real fit to be run on the seven records; it was (§31.9b), and it refutes the power law the
> conversion below assumes. ⭐ **§31.9a's conclusion — never gate on the Soret sign — survives**, with a
> margin of 2.2× rather than 5.4×. The block is kept because it is what prompted the fit.

#### ⚠ THE SIDE FINDING AS FIRST WRITTEN — the pedestal exponent may be ≈ 0

`k` is a two-point estimate of the pedestal's spectral slope. With band centres 454 and 530 nm,

```
   k = (530/454)^n   =>   n = 0.32          Rayleigh n = 4;  large Mie droplets n -> 0
```

⛔ **`SPEC_capture_quality.md` §16.12.2B pre-registered this exact reading**: *"n lands in 2–4 → droplets
growing, Ostwald ripening observed directly"*, against *"**n ≈ 0** → it is a flat offset, not scatter, and
§16.12.2 is wrong."* ⭐ **This estimate lands near the second branch**, on a 13× lever arm, 20 rows, from data
that has been on disk since 2026-08-18.

⚠ **Do not promote this to a verdict from here.** It is **two band means, not §16.12.2B's ~50-point λ⁻ⁿ fit**;
the bands are wide; `k` and `n` trade against a genuine flat offset by that section's own caveat; and it
measures the slope of the material that *left* the beam, which need not equal the slope of what remains.
⭐ **Reproduce every number above with `diagnostics/soret_valley_coupling.py`** (reads the seven PDFs
directly — no fixture, no rig).

⇒ ⭐ **it makes running the real fit urgent, and it is now cheap** — the seven records carry three bands per row
and the reference spectra are attached. ⭐ It bears directly on `DOC_pedestal_correction.md`, whose premise is
that the residual is an instrument artifact rather than scatter — a near-flat exponent is *consistent* with
that document's own chapter 10, not against it.

### ⛔⛔ 31.9b §16.12.2B's λ⁻ⁿ FIT, RUN ON THE SEVEN RECORDS — the model is refuted, not the exponent  *(Edwin, 2026-08-19)*

⭐ `SPEC_capture_quality.md` §16.12.2B pre-registered the reading before any data was seen:

```
   n in 2-4, and n DECREASING run-to-run  ->  the droplets are growing: Ostwald ripening observed directly
   n ~ 0                                  ->  it is a flat offset, not scatter, and §16.12.2 is wrong
```

⛔⛔ **The measured answer is NEITHER, and §16.12.2B lists no third branch.** Three findings, in the order
they had to be established. ⭐ Reproduce all of them with **`diagnostics/pedestal_exponent_fit.py`**.

#### ⛔ 1 — THE FIT CANNOT BE RUN ON THE SHIPPED ANCHORS. `PB_BASELINE_WINDOWS`' far window is not pigment-free.

| run | A(520–540) | A(620–630) | ratio | **n (power)** | n (offset+power) |
|---|---|---|---|---|---|
| 001 | 0.1057 | 0.2558 | 2.42 | **−5.45** | −47.4 |
| 002 | 0.0810 | 0.2103 | 2.60 | **−5.91** | −53.8 |
| 003 | 0.0928 | 0.2189 | 2.36 | **−5.32** | −57.8 |
| 004 | 0.0774 | 0.2036 | 2.63 | **−6.01** | −57.6 |
| 005 | 0.1076 | 0.2498 | 2.32 | **−5.21** | −54.8 |
| 006 | 0.0897 | 0.2221 | 2.48 | **−5.62** | −58.0 |
| 007 | 0.0918 | 0.2368 | 2.58 | **−5.89** | −58.8 |

⛔ **`n` is negative on every run — absorbance RISES toward the red inside the "baseline".** That is not a
scattering pedestal; it is **protochlorophyll Qy at ~623–626 nm sitting inside the 620–630 window.** ⭐ The
windows were only ever a *straight-line anchor pair*; nothing ever claimed they were pigment-free, and
§16.12.2B inherited them without checking. ⚠ The pigment-light stretches actually are **505–515** (A ≈ 0.086)
and **595–605** (A ≈ 0.122); 620–630 sits on the rising Qy flank.
⚠ Two smaller corrections while we are here: the windows hold **207 points**, not §16.12.2B's *"~50"* (the
grid is finer than it assumed), and the 3-parameter `c + k·λ⁻ⁿ` form is **degenerate exactly as that section's
own caveat predicted** — `c` runs to the window mean and `n` to nonsense.

#### ⛔ 2 — AND THE ARCHIVE COULD NOT SUPPORT THE FIT ANYWAY

⭐ **Only the WINNER spectrum of each run was persisted** (§9.1a, §27.25). ⇒ there is **no within-run pair of
full spectra at two turbidities**, which is what a pedestal fit needs; seven winners are seven different fills.
⚠ Between-run difference spectra do not substitute: 003 − 004 (the two halves of one dilution) reads
**−0.079 at 450 nm** — pigment, not scatter. ⇒ ⭐ **the only spectrally-resolved time series in the archive is
three band means per decision row**, and that is what the rest of this section uses.

#### ⛔⛔ 3 — ON THOSE THREE BANDS THE POWER LAW ITSELF IS REFUTED

Within one run the pigment concentration is fixed, so `d(band)/d(A_valley)` isolates whatever leaves the beam.
⭐ **A λ⁻ⁿ pedestal must make that slope MONOTONE in wavelength.** Measured:

| | soret (454 nm) | valley (530 nm) | qBand (572 nm) |
|---|---|---|---|
| 006 rows 0–8 — the 13× sweep | 1.065 | 1.000 | **1.302** |
| 006 rows 9–19 — the tail | 1.900 | 1.000 | **1.494** |
| 004, whole run | 2.126 | 1.000 | **1.406** |
| 007, whole run | 2.223 | 1.000 | **1.453** |

⛔⛔ **The redder band moves MORE than the valley, and so does the bluer one — an interior minimum. No power
law, at any exponent, has one.** Solving the sweep for `n` band by band gives **+0.40 from the Soret and −3.42
from the Q band**; Rayleigh predicts **+4.0 at both**. ⇒ the two estimates are not a noisy pair, they are
**incompatible**, and it is the model that fails.

⚠ **Candidate readings, none established here.** Something that multiplies the pigment's *own* bands would
produce exactly this shape — **pathlength amplification by multiple scattering**, or **pigment leaving the beam
inside the droplets it is dissolved in** (§16.12.7d's inference, arriving in the data). ⛔ Both are hypotheses;
this section establishes only that a single-exponent pedestal is not what is there.
⚠ **And one confound on the sweep row**: at `A_Soret ≈ 2.0` the transmission is ~1 %, where detector
nonlinearity and stray light compress the reading. ⇒ the **tail** figure is the trustworthy one, and the sweep's
1.065 should not be quoted alone.

#### ⭐⭐ 4 — WHAT THE POOLED FIT GIVES INSTEAD, AND IT IS BETTER THAN WHAT §31.9a USED

`soret_ij = a_i + k·valley_ij + b_i·t_ij` — one common `k`, a per-run intercept **and** a per-run bleach rate,
identifiable because the runs differ in how `A_valley` moves against time:

| | **k** | rms | points |
|---|---|---|---|
| all rows, all runs | 1.055 ± 0.013 | 0.0095 | 74 |
| ⭐ **006 truncated to its tail** | **1.490 ± 0.032** | **0.00043** | 65 |

⭐⭐ **`k` is not a constant — 1.06 at `A_valley ≈ 1`, 1.49 at `A_valley ≈ 0.09`.** That is a second, independent
way to see that one exponent does not describe this sample. ⇒ **`k = 1.49 ± 0.03` is the value for the regime
we actually measure in**, and it supersedes §31.9a's 1.05.

⭐ **The same fit hands over each fill's photobleaching rate**, and this is the number that matters downstream:

| 001 | 002 | 003 | 004 | 005 | 006 | 007 |
|---|---|---|---|---|---|---|
| −0.0031 | −0.0028 | **−0.0113** ⛔ *(§29.1's −0.482 run)* | −0.0037 | −0.0074 | −0.0043 | −0.0038 |

⇒ **a 4.0× spread across seven fills of one oil in one evening.**

#### ⚠ 5 — WHAT IT DOES TO §31.9a

| break-even (`abs(b)/k`, at k = 1.49) | rise rate the fill must exceed |
|---|---|
| gentlest fill (−0.0028/min) | 0.0019 /min |
| median (−0.0038/min) | 0.0026 /min |
| harshest fill (−0.0113/min) | 0.0076 /min |

The 2026-08-19 fill rose at **0.0012 /min**: scattering lift `k·ΔA_valley = +0.0219` against bleaching
`|b|·Δt = 0.0480` — ⭐ **still 2.2× larger, so the conclusion holds and the Soret falls either way.**
⚠ **But the margin is 2.2×, not §31.9a's 5.4×, and only 1.6× against the gentlest fill.**

⭐⭐ **So the reason not to gate on the sign gets stronger, not weaker, and it changes shape:** the break-even
is not a constant to be checked against — **it depends on THIS fill's bleach rate, which varies 4× and cannot
be known while the run is still going.** A gate whose threshold is only knowable afterwards is not a gate.

⛔ **WITHDRAWN, per §16.7.0's practice:** §31.9a's **`n = 0.32`**. It converted a band-pair coupling into an
exponent through the very power law finding 3 refutes. `k = 1.49` is a coupling between two bands and nothing
more. ⚠ §31.9a's `k = 1.05` is not wrong — it is the high-turbidity value, correctly measured on the wrong
regime for our purposes.

#### ⭐ WHAT §16.12.2B SHOULD SAY NOW

⛔ **Do not re-run it on `PB_BASELINE_WINDOWS`.** If the question is still worth asking, it needs (a) genuinely
pigment-free windows — **505–515 and 595–605** are the candidates on this instrument, and even those are only
*local minima*, not proven pigment-free; and (b) **row spectra**, which the engine does not persist. ⚠ (b) is
the real blocker and it is a §9.1a decision, not an analysis one.
⭐ **Its underlying question is answered in the negative regardless**: whatever the residual pedestal is, it is
**not a single-exponent scattering term**, so neither *"n in 2–4 ⇒ ripening observed"* nor *"n ≈ 0 ⇒ flat
offset"* can be concluded from this archive. ⚠ This bears on `DOC_pedestal_correction.md`, whose position is
that the residual is an **instrument artifact rather than scatter** — finding 3 is *consistent* with that
document's chapter 10, and it removes the λ⁻ⁿ fit from the list of things that could still overturn it.

### ⭐ 31.10 ACCEPTANCE — what must be shown, not argued

1. ⭐⭐ **Replay `20260819/001`'s 43 rows through `decide()` alone** (§11.9b's CSV-replay harness): TEST C
   fires at **row 10, t = 3.06 min**, outcome `DEGRADING_FILL`, answer **13.585 at 6.32 s** — ⭐ *bit-identical
   to the value the shipped code produced*, at 24 % of the lamp dose.
2. ⭐ **All seven series F runs replay unchanged** — same outcome, same branch, same value, TEST C never fires.
   ⛔ A single changed value here blocks the whole section.
3. ⭐ **The re-clouding fixture still takes TEST B**, `huntFrom` still moves to 5, and it still reads the
   vertex at 13.42 / 6.6 min (§30.17).
4. ⚠ **A synthetic "cleared then ripened" curve** takes the vertex, not the first look — the §31.5 exception
   must be shown to be conditional, not a blanket refusal.
5. ⚠ **A flat noisy fill of 43 rows does not fire C** at the shipped constants.

### ✅⭐⭐ 31.11a AS BUILT — C1 · C2 · C3 · C4 · C5, 2026-08-19  *(460 tests green, was 452; ⏸ **only C6, the rig session, remains** — §31.11b)*

⭐ **Everything §31 specifies is implemented and green.** `MonitorOutcome.DEGRADING_FILL` (core, added to
`hasValue`); `DEGRADE_TREND_ROWS/SIGMA/RISE_FRACTION/CONSECUTIVE`, `__degradingTrend`, `__isDegrading`,
`__degradingDiagnostics` and `__fireDegraded` in `ClearingEvaluator`; the §31.5 refusal inside `__read`; the
§31.8 note on the held gate; the coach line and the outcome glossary. `tests/test_degrading_fill.py` — 8 tests.

⭐ **The acceptance gate of §31.10 was met on the first run**, and the constants were NOT retuned:

| §31.10 | result |
|---|---|
| 1 · replay `20260819/001` | ⭐ TEST C fires on **row 10, t = 183.3 s (3.06 min)**, outcome `DEGRADING_FILL`, answer **13.585 at 6.3 s** — bit-identical, at **24 % of the lamp dose** |
| 2 · seven series F runs unchanged | ✅ `test_series_f_replay` — 7 runs × 3 assertions, untouched |
| 3 · re-clouding fixture still TEST B | ✅ `test_clearing_evaluator` — 25 tests with the replay, all green |
| 4 · "cleared then ripened" keeps the vertex | ✅ — ⚠ **but not by the route §31.5 imagined; see below** |
| 5 · a flat noisy fill does not fire C | ✅ 43 rows, deterministic wobble, `SETTLED_IMMEDIATE` |

#### ⛔⛔ ONE DEFECT THE BUILD SHIPPED AND THE RIG PLAN CAUGHT — the status line called it settled

⭐ **`hasValue()` returns True for `DEGRADING_FILL`, and that is deliberate** — the first look *is* the answer,
and every consumer that asks "did this run produce a number?" must say yes. ⛔ **But `CapturePanel` branches on
exactly that predicate**, so the one line the operator reads while measuring would have greeted a fill that was
coarsening throughout with:

```
   ✅ settled after 3:03 — qPercent 13.59 (FIRST_SETTLED_WINDOW)
```

⛔⛔ **That is precisely the lie §31.7 rejected `SETTLED_IMMEDIATE` for, reintroduced one layer up.** The
outcome was honest, the glossary was honest, the coach line was honest — and the status bar, the only one of
the four the operator cannot miss, was not. ⭐ It was found by walking the paths a `DEGRADING_FILL` run travels
*before* the rig session rather than during it, which is the whole argument for doing that walk.

⇒ the status line now names the degradation, keeps the value, and says what to do:

```
   ⚠ the fill was DEGRADING, not settling — qPercent 13.59 read from the first look after 3:03.
     The value stands (the earliest look is the least contaminated), but PREPARE A FRESH DILUTION
     before measuring again.
```

⚠ **The general lesson, worth carrying**: `hasValue()` answers *"is there a number?"* and nothing else. Any
caller that treats it as *"did this go well?"* is wrong the moment an outcome carries a value **and** bad news.
`DEGRADING_FILL` is the first such outcome; it will not be the last.

#### ⭐⭐ THE DIVISION OF LABOUR FALLS OUT OF THE GUARD, RATHER THAN BEING DESIGNED IN — a finding from the build

§31.5 reasons about a fill that clears, turns, and *then* ripens, and specifies that it keeps its vertex.
⭐ **Measured: the gate reaches that shape first, and TEST C never fires on it.** Once the valley has a
maximum *behind* it, `__hasFallenSinceMaximum` passes trivially, TEST A finds the post-turn rows flat, and
the vertex is read within two rows — long before TEST C's ten-row baseline has cleared the falling tail.
And once `__gateIndex` is set, `decide()` short-circuits to `__read` and the tests are never consulted again.

⇒ ⭐⭐ **the two tests partition the space exactly, and the guard is the partitioner**: a fill whose turbidity
ever fell goes to the gate; a fill whose turbidity never fell is precisely the one the guard would have
stalled forever, and that is what TEST C receives. ⚠ **The §31.5 refusal is therefore a SAFETY property, not
a branch this shape reaches** — it is exercised by run 001, where `valleyFell` is `False`. ⛔ Keep it: it costs
nothing, it is the safe direction, and a future cadence or θ change could move the race.

### ⭐ 31.11 PHASED  *(C1–C5 — ✅ ALL BUILT, see §31.11a)*

| | | |
|---|---|---|
| **C1** | `__isDegrading` + constants (`DEGRADE_TREND_ROWS = 10`, `DEGRADE_SIGMA = 4.0`, `DEGRADE_RISE_FRACTION = 0.01`, `DEGRADE_CONSECUTIVE = 2`), wired into `decide()` per §31.6, with the replay test of §31.10.1 | ⭐ the whole finding |
| **C2** | `__fireDegraded` + the §31.5 `argmin(A_valley)` refusal + `valleyFell` diagnostic | ⛔ without this C1 can still report a crossover vertex |
| **C3** | `DEGRADING_FILL` outcome, `hasValue`, glossary, coach line, report header | the operator hears it |
| **C4** | the §31.8 note on the stalled guard | cheap, independent |
| **C5** | ⚠ regression replay of all seven series F records + the re-clouding fixture (§31.10.2–3) | ⛔ the gate on shipping any of it |
| ⏸ **C6** | ⚠ **THE RIG SESSION — §31.11b. NOT RUN.** Four arms on real glass | ⛔ the constants are calibrated on **one** run and have never met a camera |

⚠ **C1–C4 are ~60 lines in `DevSpectralPlugin.py` plus one enum member.** ⛔ **C5 is the expensive half and
the one that decides whether the constants are right** — it is not optional, and the constants above are
calibrated on **one run**.

### ⏸⭐⭐ 31.11b C6 · THE RIG SESSION — SPECIFIED, NOT RUN  *(owed, 2026-08-19)*

⛔ **Everything in §31 was derived from ONE run and has never met a camera.** ⚠ `pytest` proves the arithmetic
reproduces an archived trace; it cannot prove that a real aged fill on real glass produces that trace, and it
cannot prove that a *good* fill is left alone. ⇒ this is the gate, and it is Edwin's to run.

⚠ **Restart the app first** — the plugin is injected from disk, so a running bench holds the old evaluator.
All arms: the DEV bench, `Frames = 60`.

#### ⚠ PREP — the one thing with lead time

TEST C only ever receives fills whose turbidity **never falls** (§31.11a's partition), and a fresh fill clears
and goes to the gate. ⇒ **a dilution must stand overnight, undisturbed.** ⛔ Do NOT shake or re-stir it before
measuring (§11.4a): agitating an aged fill re-suspends coarse sediment and turns it into a different
experiment. A second, older jar is free extra data.

#### ⭐⭐ ARM A — a FRESH fill must NOT trip it  *(run this first)*

Normal protocol: bath, pre-warmed holder.

| gate | |
|---|---|
| outcome | `SETTLED_IMMEDIATE` or `SETTLED_AFTER_CLEARING` |
| status line | begins `✅ settled after` |
| the word "degrading" | ⛔ appears nowhere |
| `gate at` | the familiar 1.7–5 min |

⛔⛔ **If TEST C fires on a good fill, STOP the session.** A false positive costs a real measurement, and the
constants would have to be re-derived before anything else in §31 is trusted.

#### ⭐⭐ ARM B — the AGED fill: does it fire on real glass?

⭐ **Watch the status bar during the run**: the coach line should turn amber and read
*"⚠ the fill is getting cloudier, not clearer — reading now"*.

| gate | expected |
|---|---|
| run length | ⭐ **~3 min** (ten decision rows at ~18 s), not 12+ |
| status line | `⚠ the fill was DEGRADING, not settling — … PREPARE A FRESH DILUTION` |
| Settling tab → Outcome | `DEGRADING_FILL`, with the tooltip explaining it |
| the answer's `t` | **~6 s** — the FIRST look, not a later one |
| `Q%` | inside the 12–22 domain, verdict still rendered |

⚠⚠ **A NULL HERE IS NOT A FAILURE, and must not be recorded as one.** If the aged jar's `A_valley` *falls*, it
sedimented rather than ripened: the arm is **void**, TEST C is untested, and what we learn instead is **how old
"old" has to be** — which §31 currently does not know and has no way to guess.

#### ⭐ ARM C — the record

The four new diagnostics must be present and healthy: `degradingPerMinute`, `degradingSignificance` (⭐ should
be *comfortably* above `DEGRADE_SIGMA = 4`, not scraping past it — 001 replayed at 21), `degradingRisePercent`,
`degradingRows = 10`, and `valleyFell = false`.
⚠ **Look at the settling curve tabs at this length.** Ten rows is a third of what those plots have ever been
drawn with; if they read badly that short, it is a finding and it belongs to §27.22's family.

#### ⚠ ARM D — optional, and it targets the one risk §31.9 leaves unmeasured

§31.9 records, unmeasured, the possibility of **a slow re-cloud that would have recovered, ended early by
TEST C**. It can be provoked deliberately: a bath-warm jar into a **cold** holder (lamp just on, or a cool
room) is §14.5's re-clouding case.

- fires **TEST B** (*"re-clouded — warming again …"*) ⇒ ⭐ the two tests separate cleanly on real glass
- fires **TEST C** ⇒ ⭐ we have found the false-positive mode deliberately and cheaply, which is worth more
  than a clean pass

#### ⭐ WHAT MUST BE WRITTEN DOWN

**Fill age in hours**, room temperature, holder state (pre-warmed or not), and whether the jar was moved
before insertion. ⇒ §31's constants come from a single run; **the first real evidence on how aged a fill must
be before it ripens comes from this session and from nowhere else.**

### ⛔ 31.12 WHAT THIS SECTION DOES NOT DO

- ⛔ **It does not detect a bad fill before the lamp goes on.** Three minutes of dose is the floor as
  specified; a pre-check on the very first window is a different design.
- ⛔ **It does not rescue the measurement.** The answer is still the first look of a fill that was already
  degrading when it arrived — ⭐ the honest verdict is *"prepare a fresh dilution"*, not a corrected number.
- ⚠ **It does not touch `depthThreshold`,** whose trend-vs-single-window weakness (§31.5) is recorded and left
  open.
- ⭐ **And it becomes vestigial the day the oil dissolves** — `SPEC_capture_quality.md` §16.12.7d's hydrocarbon
  route retires the whole settling machine, TEST C included. ⚠ That is a reason to keep it small, not a
  reason to skip it: the shipping solvent is isopropanol today.

---

## ⭐⭐ 32 · THE BILLA CLEVER TRIAD — three fills, three verdicts, two of them wrong  *(Edwin's runs 001–003 of 2026-08-19; DESIGN, not built)*

> **Records:** `spectracs-references/tmp/20280819BillaClever/{001,002,003}.pdf` (the folder name carries a
> `2028` typo; the runs are 2026-08-19, 20:50 / 21:12 / 21:32). All three under `clearing-2.0`, W = 60.
> ⭐ Every number in this section was **read out of the embedded `workflow.json`**, not re-measured — the
> `monitorRecord` of §15.2 is what made this analysis possible at all, on the same evening.
>
> ⭐ Edwin's own reading, before any of this was computed: *"001 is okay; 002 I have the feeling the `Q%`
> curve would go down to about 20 if we had waited; 003 — I think 20 would be the right choice. Maybe we
> should look at values of `Q%`."* ⭐⭐ **All three intuitions are confirmed below. The mechanism he guessed
> for 002 is not the one the data support, and the one they do support is better** (§32.7).

### 32.1 · What the three runs are, and what the instrument said

| run | fill | outcome | branch / read | **answer** | t | rows | A_valley first → last |
|---|---|---|---|---|---|---|---|
| 001 | dilution **A**, "first 4 ml" | `SETTLED_AFTER_CLEARING` | was-clearing / VERTEX | **19.866** | 807.6 s | 46 | 0.691 → 0.1279 |
| 002 | dilution **B**, "second 4 ml", **warm-bath treated** | `SETTLED_IMMEDIATE` | arrived-clear / FIRST | **20.990** | 6.7 s | 6 | 0.2076 → 0.2042 |
| 003 | dilution **B**, deliberately **clouded in the fridge** | `SETTLED_IMMEDIATE` | arrived-clear / FIRST | **8.450** | 6.6 s | 46 | 2.667 → 0.0586 |

⭐⭐ **002 and 003 are the same liquid.** That is what makes this session the most informative the archive
holds: for the first time two runs of one material were driven through **very different turbidity
histories**, and they can be held against each other.

### ⛔⛔ 32.2 · DEFECT 1 — run 003 reported the darkest row of the run, and it is off by 188 instrument floors

Run 003's `Q%` trace, in full:

```
 t/s     6.6    93   199    343   473    624    836
 Q%     8.45  17.18 34.31  26.06 21.04  20.98  20.31
 A_v    2.667 2.290 1.663  0.852 0.205  0.085  0.0586
        ^ REPORTED           ^ peak        ^ the honest region
```

The evaluator gated correctly — it refused to settle for 46 rows and 13.9 minutes, exactly as designed —
and then **read the first look**: `Q% = 8.450`, against a curve whose last and best value is `20.310`.
⇒ **an error of 11.86 units = 188 × the 0.063 no-re-seat floor.** It is by a wide margin the worst number
the instrument has ever produced, and nothing in the outcome (`SETTLED_IMMEDIATE`) says so.

#### Why it happened, exactly

`__depthOf()` asks *"how far below its **first look** does the `Q%` minimum sit?"* On 003 the first look **is**
the minimum of the whole run, so `depth = 0.000` against `depthThreshold = 0.126`, and §29.3's first rule
fires: *"no turning point deeper than this window's own noise ⇒ nothing has happened since the first look
but photodamage, so the first look IS the least-damaged measurement of the run."*

⛔ **The premise is false here.** A great deal happened since the first look, and none of it was photodamage.

#### ⭐ The record already contained its own refutation

The promoted answer carries `diagnostics.valleyFell = true` on the branch named `arrived-clear`. **The
evaluator computed "the turbidity fell" and then filed it beside "the fill arrived clear."** §31.5 consults
`valleyFell` only when `__degrading` is latched; on a fill that clears and never trips TEST C, the
contradiction is recorded and ignored.

#### ⚠ And `MATERIAL_FALL` was half right

§30.1 deleted `MATERIAL_FALL = 0.010` with the argument that it *"took the decision about HOW TO READ `Q%`
from a DIFFERENT QUANTITY"*. That argument is sound for choosing **where the minimum is**; it is **wrong for
deciding whether the first look is admissible at all**, because "did this fill arrive clear?" is a question
about turbidity and can only be answered by the turbidity. ⇒ §32.7's C2 puts a turbidity term back, in a
scale-free form, and only in front of the first-look branch.

### ⛔⛔ 32.3 · THE PHYSICS FINDING — `Q%` is NOT monotone in turbidity, and §1's founding premise is refuted

§1 states the whole design in one picture: *turbidity falls and `Q%` falls with it; photodamage grows and
`Q%` rises; they cross; the minimum is the truth.* Run 003 traverses **eight times more turbidity than any
run before it** and shows the relation is a **hump**:

```
Q%                34.3 ┐  peak, at A_valley = 1.663
                       │╲
                  20.3 ┤ ╲__________  the asymptote, A_valley -> 0
                       │
                   8.5 ┘  A_valley = 2.667   <- the "minimum" the read rule selected
                       └───────────────────────────────
                        2.7      1.7      0.8      0.06   A_valley
```

⭐ Below `A_valley ≈ 1.7` the archive's rule of thumb holds: **more turbidity ⇒ higher `Q%`.** Above it the
relation **reverses**, and a fill entering the beam above the hump produces its lowest `Q%` at its worst
moment. ⇒ **on such a fill the `Q%` minimum is not a settling point at all, and any rule that hunts a
minimum over the whole run will find the wrong end of it.**

⚠ **Do not model the reversal as a λ⁻ⁿ scattering pedestal.** A pedestal with n = 4 predicts
`dQ%/dp = −87.6` at 003's clear end — i.e. turbidity would *lower* `Q%` everywhere, which contradicts the
+4 to +5 measured in §32.6 and every earlier observation. §31.9b already refuted the λ⁻ⁿ model on the seven
Lugitsch records; this is the second independent refutation, from the other end of the turbidity range.
⭐ The hump is **empirical**; §32.4 explains at least its upper limb without any optics at all.

### ⛔⛔ 32.4 · DEFECT 2 — there is a floor on absorbance and **no ceiling**, and 21 of 003's 46 rows are dark-floor arithmetic

`V_SORET_FLOOR = 0.15` rejects a row whose Soret is too *small*. Nothing rejects one whose Soret is too
*large*. Run 003's first look reports `A_Soret = 2.979`:

```
A = 2.979  =>  the sample transmits 0.105 % of the reference
reference in its own DN target (DN_TARGET_LOW/HIGH = 20-50 DN)
          =>  the sample sits at 0.02 - 0.05 DN  --  below one code of an 8-bit YUYV sensor
```

⇒ **the first six rows of run 003 are not measurements of oil. They are arithmetic on the dark floor**, and
the smooth 8.45 → 17.18 ramp they trace is the floor releasing its grip as the fill clears, not a spectrum.
That is the honest explanation of the hump's upper limb, and it needs no optics.

⭐⭐ **THE CONSTANT ALREADY EXISTS IN THE FILE.** `VALUE_CEILING = 1.5` — *"drop saturated-Soret λ (A > 1.5)"*
— is applied inside the band machinery and **never reaches `monitorMetrics()`**. The guard was reasoned,
written down, and then not wired to the one caller that can burn 14 minutes of lamp on the strength of it.

⚠ **THE TABLE BELOW IS STALE AND IS KEPT AS WRITTEN — see §51.4.** It was measured before runs 004–007
existed. The ceiling in fact touches **five** runs, not three: Lugitsch 006 (5 rows), Billa 001 (2), **Billa
003 (21)**, Billa 005 (6), Billa 006 (1). ⭐ The conclusion is unchanged and stronger — it costs none of them
an answer except 003.

What a ceiling at 1.5 costs the archive, measured over the twelve monitored runs that existed on 2026-08-19:

| run | max A_Soret | rows > 1.5 | first admissible look | its `Q%` | answer changes? |
|---|---|---|---|---|---|
| Lugitsch 001–005, 007 | 0.856 – 0.992 | **0** | t = 5.5 s | — | no |
| 20260818A/001 | 0.875 | **0** | t = 5.5 s | — | no |
| 20260819/001 (TEST C) | 0.680 | **0** | t = 6.3 s | — | no |
| Lugitsch 006 | 2.019 | 5 | t = 81.1 s | 15.747 | **no** (vertex stays 13.972) |
| BillaClever 001 | 1.641 | 2 | t = 38.1 s | 21.447 | **no** (vertex stays 19.866) |
| **BillaClever 003** | **2.979** | **21** | **t = 380.6 s** | **23.936** | ⭐ **8.450 → "keep waiting"** |

⭐⭐ **A fix that changes exactly the one run it was written for, and nothing else in the archive.** That is
the property to demand of every change in this section.

#### ⛔⛔ 32.4a · AND IT COLLIDES WITH THE SUB-FLOOR ABORT — the same representation, the opposite prognosis

`decide()` treats a row with no `values` as evidence that the **measurement is broken**:

```python
if len(decisions) >= 2 and not any(row.values for row in decisions[-2:]):
    return MonitorDecision(stop=True, outcome=MonitorOutcome.MEASUREMENT_BROKEN, ...)
```

⇒ if an over-ceiling row is represented as `values = {}` like a sub-floor row, **run 003 aborts at t ≈ 40 s
as `MEASUREMENT_BROKEN`** — a different wrong answer, arrived at faster.

⭐ The two conditions are the TEST B / TEST C motif again: *same observable, opposite prognosis.*

- **sub-floor Soret** — no light is being absorbed; there is nothing in the cuvette; **abort, the fill cannot
  produce a number.**
- **over-ceiling Soret** — too much light is being absorbed; the cuvette is full of a fill that is still
  clearing; **wait, it will produce a number.**

⇒ they need **two states, not one**: `values = {}` keeps its meaning, and a new `tooDark` row-state means
*"not a look, keep looking"* — it never reaches the gate, never enters the hunt, and **never counts toward
the broken-measurement abort**. A run that stays over the ceiling to the 25-minute cap ends with no value,
which is the right ending for a fill too cloudy to read.

### ⚠ 32.5 · DEFECT 3 — run 002: the gate is a **rate** test with no **level** term, and it settled on a turbid plateau

002 was warm-bath treated, entered the beam at `A_valley = 0.2076`, and **stopped clearing**:

```
t/s      6.7    23.1   41.8   60.6   79.5   98.5
A_v    0.2076 0.2050 0.2057 0.2056 0.2060 0.2042   -> -0.0022 /min  (theta = 0.005)  FLAT
Q%     20.990 21.047 21.076 21.094 21.145 21.164   -> +0.1089 /min at 11.2 sigma     RISING
```

TEST A is satisfied twice and the gate fires at 98.5 s, 1.6 minutes after insertion. **On its own terms the
evaluator is not wrong**: the turbidity is not moving, the `Q%` curve has no turning point, so the first
look is the least-damaged one. It reports 20.990.

#### ⭐⭐ The cross-run evidence that 20.990 is high — and it is the cleanest the archive has

Run 003, **the same liquid**, sweeps down through 002's turbidity level on its way to clear:

```
003 crosses A_valley = 0.2053 at t = 473 s   ->  Q% = 21.035
002 sat at A_valley  = 0.204 - 0.208         ->  Q% = 21.086  (mean of its six looks)
                                                  ------  agreement: 0.05  ( < 1 instrument floor )
003 then continues to A_valley = 0.0586      ->  Q% = 20.310  ( a further -0.725 )
```

⭐⭐ **`Q%` is a reproducible function of `A_valley` for a given material.** Two fills of the same liquid,
prepared differently, measured half an hour apart, agree to 0.05 at the same turbidity — and the one that
kept clearing shows there were **0.725 units still to fall**, eleven instrument floors.

⇒ 002's plateau was **not clear. It was stalled.**

#### ⛔ And the level test that would catch it is NOT derivable from the archive

| terminal `A_valley` | run |
|---|---|
| 0.0586 – 0.105 | BillaClever 003, TEST-C 001, all seven Lugitsch |
| 0.1279 | BillaClever 001 |
| 0.1510 | 20260818A/001 |
| **0.2042** | **BillaClever 002** ⛔ the highest in the archive |

002 tops every ranking — absolute (0.204), over Soret (0.215 vs 0.079–0.173), over `A_Q` (0.503 vs
0.283–0.432) — but **the gap to the next run is 1.35×, not the 15× that licensed `depthThreshold`** (§29.2).
⛔ Any threshold planted between 0.151 and 0.204 today would be a number chosen to separate two runs, one of
which is a different oil. ⇒ **do not plant one.** §32.6 offers something better than a threshold.

### ⛔⛔ 32.6 · κ, the turbidity contamination coefficient — ⚠ **DEMOTED BY §33.** Edwin answered *"same stock"*, and a one-coordinate correction cannot survive that answer. Kept because the observation inside it is real and §33 builds on it.

Edwin's *"maybe we should look at values of `Q%`"*, taken literally: plot `Q%` against `A_valley` instead of
against time. In the post-clearing region the relation is **linear**, and it is the same relation on two
independent runs:

| run | fit window | n | lever arm in `A_valley` | **κ = d`Q%`/d`A_valley`** | intercept at `A_valley` = 0 | r |
|---|---|---|---|---|---|---|
| BillaClever 001 (dil. A) | `A_v ≤ 0.25` | 28 | 0.116 | **+4.03** | 19.377 | +0.955 |
| BillaClever 003 (dil. B) | `A_v ≤ 0.25` | 20 | 0.147 | **+6.26** | 20.217 | +0.714 |
| BillaClever 003, two-point (0.205 → 0.0586) | — | — | 0.147 | **+4.94** | — | — |

⇒ **`Q% ≈ Q₀ + κ·A_valley` with κ ≈ 4.5.** Residual turbidity does not merely add noise; it adds a *bias
proportional to how cloudy the fill still is*, and that bias is **estimable from the same two numbers the
monitor already records on every row.**

#### ⭐⭐ Applied to the same-material pair, it reconciles them to 0.01

```
kappa   002 (A_v 0.2076) ->    003 (A_v 0.0586) ->    gap
 3.5           20.264                 20.105          0.159
 4.0           20.160                 20.075          0.085
 4.5           20.056                 20.046        ⭐0.010
 5.0           19.953                 20.017          0.064
 6.0           19.745                 19.958          0.213
                                        uncorrected gap: 0.681  ( 11 instrument floors )
```

⭐ **The correction is insensitive to κ over the whole plausible range** — anywhere in 3.5–6.0 it removes at
least three quarters of the disagreement. And it lands where Edwin said it would:

> *002 → **20.06**, 003 → **20.05**.* His "about 20" for both, from two runs that reported 20.990 and 8.450.

⭐⭐ ⇒ **his intuition was right and his mechanism was not.** 002 was never going to fall to 20 by waiting —
its turbidity was flat and its `Q%` was *rising* at 11σ. It reaches 20 by **correction**, not by patience.
That distinction is the difference between a protocol that costs 14 minutes of photodamage and one that
does not.

#### ⛔ Three things this does NOT yet establish, and they are why C4 is gated

1. ⛔ **κ is confounded with dose.** Both fits run along a trajectory where turbidity falls *while the lamp
   browns the sample*. The two effects push `Q%` in opposite directions, so the measured κ is a **lower
   bound** on the true turbidity sensitivity — but its size is not clean. ⇒ κ must be measured with
   turbidity varied **independently of dose** (§32.10).
2. ⛔ **It does not reconcile 001 with 002/003.** Corrected, 001 (dilution A) reads 19.29 against the pair's
   20.05 — the correction moves it *away*, from 0.44 apart to 0.76. Either the two pours are genuinely
   different material, or `A_valley` is the wrong regressor because it contains **real pigment absorption as
   well as turbidity**, and only the turbidity part should be corrected. ⚠ Normalising by `A_Soret` does not
   rescue it (19.20). ⭐⭐ **ANSWERED 2026-08-19: SAME STOCK** ⇒ §33. *(the question as put: were A and B two pours of one
   stock — in which case they must agree and this is a real defect in the correction — or two separately
   made dilutions?)*
3. ⛔ **The intercept is not a per-run quantity.** Refitting `Q%` on `A_valley` run-by-run gives 12.0 – 22.2
   across the seven Lugitsch runs, which all sit within 0.04 of each other in `A_valley` — **no lever arm,
   so the fit fits noise.** ⇒ a per-run extrapolation to zero turbidity is **refused**, measured, not
   argued. κ must be a **calibrated constant**, applied as a correction, never a per-run slope.

#### ⚠ And if κ is real, it re-prices the whole archive

At κ = 4.5 the turbidity carried into every archived answer is:

| run set | `A_valley` at the read | contamination `κ·A_v` | in instrument floors (0.063) |
|---|---|---|---|
| Lugitsch A (seven) | 0.069 – 0.105 | 0.31 – 0.47 | **5 – 7** |
| BillaClever 001 | 0.129 | 0.58 | **9** |
| BillaClever 002 | 0.208 | 0.93 | **15** |

⇒ ⚠ **every number the instrument has ever produced sits several floors above its own zero-turbidity value**,
and the size of that offset varies with how well the fill happened to clear. That is a **bias**, not a noise
term, and `SPEC_capture_quality.md` §16.24's error budget does not contain it. ⛔ Contingent on κ — stated
here so that it is checked, not so that it is believed.

### ⭐ 32.7 · THE RULE CHANGES

⭐ Ordered by confidence. **C1 and C2 are corrections to a broken read and should land together; C3 is a
verdict, not a read; C4 is a research result that needs an experiment before it is allowed near an answer.**

#### ⭐⭐ C1 — an absorbance CEILING, with its own row state *(the load-bearing fix)*

- a monitored row whose `A_Soret` exceeds `V_SORET_CEILING` (= the existing `VALUE_CEILING`, 1.5) is
  **`tooDark`**: it produces no metric, enters no window, and **is not evidence of a broken measurement**
  (§32.4a).
- the coach says so — *"too dark to read — still clearing"* — instead of the current silence.
- the run ends at the cap with **no value** if it never comes under the ceiling. ⭐ That is the correct
  ending for a fill nobody can measure, and it is the ending 003 should have had at 6 minutes rather than
  the answer it got at 14.
- ⚠ the ceiling belongs on the **monitored bands**, plural: a fill can be over the ceiling at 454 nm and
  under it at 572 nm, and a `Q%` built from a floor-limited Soret and a valid Q band is worse than one built
  from neither.

#### ⭐⭐ C2 — the `Q%` hunt is restricted to looks taken at a comparable turbidity

Generalise §30.8. Today only a re-clouding event moves `huntFrom`; the argument it rests on — *"everything
before this row belongs to a fill that was cloudier than the one now being measured"* — **applies to the
turbid opening of every clearing fill**, re-cloud or not.

```
eligible looks  =  rows with  A_valley <= K * min(A_valley so far)          K = 2
```

- ⭐ it is a **ratchet**: the running minimum only falls, so the window only advances — the same shape as
  `huntFrom`, computed from the quantity that justifies it rather than from an event.
- ⭐ it subsumes the re-cloud case: a re-clouded row leaves the window on its own.
- ⭐ **`depth` finally means what its docstring says** — how far the minimum sits below *the first
  comparable look*, not below the cloudiest row of the run.

Replayed over all twelve archived runs at **K = 1.5, 2.0 and 3.0**:

| | K = 1.5 | K = 2.0 | K = 3.0 |
|---|---|---|---|
| eleven runs | answer reproduced to ≤ 0.001 | ≤ 0.001 | ≤ 0.001 |
| BillaClever 003 | 8.450 → 20.310, **argmin is the newest look ⇒ keep waiting** | same | same |

⭐⭐ **Insensitive across a factor of two in K, and it changes exactly one run.** K = 2 sits mid-plateau, in
the §27.26 habit.

#### ⭐ C3 — 002 gets a **fill-quality verdict**, not a different number

⭐ The read on 002 was not wrong; **the fill was.** ⇒ do not chase 002 with a read rule. Report, at the
answer (§17/D5):

- `A_valley` at the promoted row, and — once C4 lands — the implied contamination `κ·A_valley`;
- ⛔ **`clearingObserved`** — the fractional fall of `A_valley` from the run's first admissible look to the
  read. 002: **1.6 %**. 003: 97.8 %. Lugitsch: 1–7 %.
- ⚠ `clearingObserved` alone cannot condemn a fill — a genuinely clear fill also shows no fall (Lugitsch
  001/002/005 settle honestly in 105 s at `A_valley` ≈ 0.08–0.10). **It is the pair (level, fall) that is
  diagnostic**, and until §32.10 supplies a level there is no threshold. ⇒ **record both, gate on neither.**

#### ⛔ C4 — the κ correction: ⚠ **WITHDRAWN BY §33.7.** Kept for the record; do not build it.

- ⛔ **Never applied to a raw look.** At 003's first row, `20.31 − 4.5 × 2.667 = −3.55`. The relation is
  linear only in the clear regime, so the correction is a **residual** correction applied *after* C1 and C2
  have removed everything that is not a measurement of a nearly-clear fill.
- ⛔ **Never folded into the answer** until κ is measured dose-independently — §2.3's rule for the
  zero-dose extrapolation, for the same reason.
- ⭐ Recorded beside it from the day it is measured, as `qPercentAtZeroTurbidity`, with κ and `A_valley`
  travelling with it so any archived number can be recomputed when κ moves.

### ⭐ 32.8 · WHAT THE THREE RUNS BECOME

| run | today | after C1 + C2 | Edwin's call | with C4 at κ = 4.5 |
|---|---|---|---|---|
| 001 | 19.866 | **19.866** (unchanged) | "okay" ⛔ **not okay — §33.3** | ⛔ 19.29, withdrawn (§33.7) |
| 002 | 20.990 | 20.990 + *"never cleared: 1.6 % fall, `A_valley` 0.204"* | "would be about 20" | **20.06** ✅ |
| 003 | **8.450** ⛔ | first 21 rows inadmissible; run continues past 836 s; reads ≈ **20.31** | "20 would be right" ✅ | **20.05** ✅ |

### ⚠ 32.9 · WHAT COULD GO WRONG — checked against the twelve records

1. ⚠ **C1 lengthens runs.** A very cloudy fill now spends its opening minutes producing no rows at all and
   may reach the 25-minute cap with nothing. ⭐ That is the point: it converts a confidently wrong number
   into an honest refusal. ⛔ But §17/U3's finish prediction has nothing to predict from while every row is
   `tooDark` — the bar must stay INDETERMINATE and the coach must explain, or the operator watches six
   silent minutes and cancels.
2. ⚠ **C2 can starve the vertex.** If the running minimum falls fast, the eligible window can hold fewer
   than the three rows `__vertex()` needs. ⭐ Already handled — the existing guard falls back to the raw
   row — but the fallback must be **recorded**, not silent.
3. ⚠ **C1's ceiling is a Soret ceiling, and dilution sets the Soret.** A deliberately concentrated dilution
   could sit over 1.5 while perfectly clear. ⭐ The archive says otherwise for the working protocol (nine of
   twelve runs never exceed 1.0), but the ceiling must be **stated in the record** so a run refused by it
   can be recognised as a dilution problem rather than a turbidity one.
4. ⛔ **None of this touches the 002 case.** After C1 and C2, 002 still reports 20.990. The only thing that
   moves it is κ, and κ is not measured yet. ⇒ **say this out loud rather than implying the triad is fixed.**
5. ⚠ **The seven Lugitsch records are `clearing-1.0`.** Their reported answers were produced by the rule
   §29 replaced, so "unchanged" above means *the rows replay to the same read under 2.0 with and without
   C1/C2* — not that the printed 2026-08-17 numbers are reproduced.

### ⭐⭐ 32.10 · THE EXPERIMENT THAT CLOSES κ — pre-registered, one session

⭐ Turbidity must be varied **independently of lamp dose**, which is exactly what the fridge trick already
does and what no run so far has exploited on purpose.

- **one dilution**, split into **five jars**. Fridge-cloud them to different degrees (0, 5, 10, 20, 40
  minutes cold) so they enter the beam at spread `A_valley` — target 0.05 / 0.10 / 0.15 / 0.20 / 0.30, all
  **under the C1 ceiling**.
- **read each one FAST** — the first admissible window, ≤ 30 s of lamp — so dose is equal and negligible
  across arms.
- ⭐ **plot `Q%` against `A_valley` across jars.** The slope is κ, free of the dose confound; the intercept
  is `Q₀` for that dilution.
- ⭐ **then let one jar run to completion.** Its within-run slope is the confounded κ of §32.6. **The
  difference between the two slopes is the dose contribution**, which the archive has never separated.

#### The decision rule, fixed before the run *(§16.34.3's habit)*

| result | verdict |
|---|---|
| across-jar κ within ±30 % of 4.5, r > 0.9 | ⭐ κ is real and calibratable ⇒ **C4 ships** |
| across-jar κ significant but far from 4.5 | ⭐ κ is real, the within-run fits are dose-poisoned ⇒ C4 ships on the **across-jar** value |
| across-jar slope not significant | ⛔ the 002/003 reconciliation was luck ⇒ **C4 is dropped**, C3 becomes the whole answer, and a level threshold must be planted after all |

⚠ **Repeat the whole series on a second oil before κ is treated as an instrument constant** — one oil cannot
tell a property of the measurement from a property of the pigment.

### ⭐ 32.11 · PHASED

| | what | depends on |
|---|---|---|
| **B1** | replay harness over the archived `monitorRecord`s — twelve runs, real `ClearingEvaluator.decide()`, assert every recorded answer reproduces before any rule moves (§19/I5) | — |
| **B2** | **C1** ceiling + `tooDark` row state + the sub-floor/over-ceiling split (§32.4a) + coach line | B1 |
| **B3** | **C2** eligibility window at K = 2; `huntFrom` becomes its degenerate case | B1 |
| **B4** | **C3** `clearingObserved` + `A_valley` at the read, into `MonitorRecord` and onto the report | B2 |
| **B5** | rig session: re-run the 003 fill (fridge-cloud a dilution) and confirm the refusal-then-answer path end to end | B2, B3 |
| **B6** | §32.10 — the five-jar κ session | B5 |
| **B7** | **C4**, only if §32.10's decision rule says so | B6 |

⭐ B1 is not ceremony. Every number in §32 was computed **outside** the evaluator, from the records; the
claim *"eleven runs unchanged"* is only worth what the real `decide()` says it is.

### ⛔ 32.12 · WHAT THIS SECTION DOES NOT DO

- ⛔ **It does not explain the hump's lower limb.** §32.4 explains the collapse above `A_valley ≈ 1.7` as the
  dark floor. Why `Q%` *rises* with turbidity from 0.06 to 1.7 is still unexplained, and λ⁻ⁿ scattering
  predicts the opposite sign (§32.3). ⇒ κ is a **measured coefficient with no model behind it**, and it must
  be labelled that way wherever it appears.
- ⛔ **It does not give 002 a better number.** Only κ can, and κ is not measured.
- ⛔ **It does not revisit `depthThreshold`,** whose single-window basis is still the open item of §31.5.
- ⭐ **And it too becomes vestigial the day the oil dissolves** — a hydrocarbon solution has no turbidity to
  correct for (`SPEC_capture_quality.md` §16.12.7). ⚠ Again a reason to keep C1–C3 small, not a reason to
  skip them: the shipping solvent is isopropanol today.

---

## ⭐⭐⭐ 33 · SAME STOCK — the answer that kills κ and names the defect underneath it  *(Edwin, 2026-08-19; DESIGN, not built)*

> ⭐ **A and B were two pours of one stock.** §32.6 said that if the answer was "same stock", the failure of
> the κ correction to reconcile 001 with 002/003 is a **real defect**. It is, and chasing it opened the
> three stored **spectra** — the promoted capture's `REFERENCE` and `SAMPLE` arrays are in the same
> `workflow.json` as the rows — which no analysis in §32 had touched.
>
> ⛔⛔ **The conclusion is worse than §32's and simpler: not one of the three fills was ever measured in a
> settled state, and the gate could not have known.**

### ⭐ 33.1 · The data confirm "same stock" before anything is concluded from it

| | A_Soret at the read | | |
|---|---|---|---|
| 001 | 0.9631 | | ⭐ 001 and 002 agree to **0.5 %** — two fills of one stock at one concentration, |
| 002 | 0.9586 | | as Beer-Lambert requires. The premise is not assumed, it is measured. |
| 003 | 0.7312 *(last row)* | | ⛔ **24 % lower.** Same stock. Same concentration. |

### ⛔⛔ 33.2 · Therefore 0.731 is what this stock reads when clear — and 001 and 002 were read at **+32 % turbidity**

Concentration is identical by construction, so **every unit of A_Soret above the clear value is turbidity**.
003 is the only fill that was ever driven down to it, because it was the only one the gate refused to let go:

```
clear (003's last row, and still falling at -1.2 %/min)   A_Soret = 0.7312
001 read at                                               A_Soret = 0.9631  = clear + 0.2319   (+32 %)
002 read at                                               A_Soret = 0.9586  = clear + 0.2274   (+31 %)
```

⭐⭐ ⇒ **the fill Edwin called "okay" was read carrying the same residual turbidity as the fill he called
wrong.** 001 is not the control. There is no control in this session.

⚠ And 0.7312 is an **upper bound** on clear: 003's own Soret was falling at 1.18 %/min when the run ended.
⇒ the excesses above are **at least** 32 %.

### ⛔⛔ 33.3 · The two fills disagree by 18 floors **at the same turbidity**, which is why no single-coordinate correction can work

| | A_Soret | A_valley | Q% |
|---|---|---|---|
| 001 (native haze) | 0.9631 | **0.1289** | 19.867 |
| 002 (warm-bath haze) | 0.9586 | **0.2076** | 20.990 |
| 003 passing through the same A_Soret (t = 473 s) | 0.9392 | 0.2053 | 21.035 |

⭐ 002 and 003 sit at the **same point in both coordinates** and read the same Q% to 0.05 — §32.5's
crossing, now confirmed in two dimensions instead of one.
⛔⛔ **001 sits at the same A_Soret with 38 % less A_valley, and reads 1.12 lower — 18 instrument floors.**

⇒ **turbidity is not a one-parameter family.** Native haze and warm-bath haze have different spectral
shape, so a fill's cloudiness cannot be summarised by any single band. **κ·A_valley was fitting a
trajectory, not a physical coefficient**, which is why it reconciled two points on 003's trajectory (002 and
003) and threw 001 further away.

⚠ ⛔ And a plain grey (Mie) pedestal does not save it either: a wavelength-flat offset **cancels in the
numerator** of `Q% = −100·(A_v − A_Q)/A_S` and inflates only the denominator, so it would make the *more*
turbid fill read *lower*. 002 reads **higher**. ⇒ neither λ⁻ⁿ (§32.3) nor grey. **We have no model of the
turbidity term, and §32's κ was a model-free stand-in that this section refutes.**

### ⛔⛔ 33.4 · WHY THE GATE COULD NOT SEE IT — it watches one band's **absolute** rate

At the row each run was read, the three monitored bands were moving like this:

| run | dA_valley | | dA_Soret | | dA_Q | | dQ%/dt |
|---|---|---|---|---|---|---|---|
| | /min | %/min | /min | %/min | /min | %/min | /min |
| **BillaClever 001** | −0.0039 | **−3.04** | −0.0102 | **−1.06** | −0.0059 | **−1.85** | **+0.0020** |
| BillaClever 002 | −0.0006 | −0.30 | −0.0023 | −0.24 | −0.0002 | −0.05 | +0.0930 |
| BillaClever 003 | −0.0046 | −7.87 | −0.0086 | −1.18 | −0.0073 | −3.52 | −0.1259 |
| Lugitsch 004 | −0.0036 | −5.18 | −0.0089 | −1.02 | −0.0048 | −2.50 | +0.0012 |
| Lugitsch 005 | −0.0047 | −4.55 | −0.0136 | −1.41 | −0.0065 | −2.70 | +0.0142 |
| Lugitsch 007 | −0.0040 | −4.64 | −0.0098 | −1.09 | −0.0058 | −2.78 | −0.0488 |
| Lugitsch 001/002/003/006, 20260818A, 20260819/001 | | −0.6 … −2.0 | | −0.3 … −1.5 | | −0.4 … −1.3 | |

⭐⭐ **Nine of the twelve archived runs were still clearing at 1–5 %/min in at least one band at the moment
they were declared settled.** `THETA_PER_MINUTE = 0.005` is an **absolute** threshold on the **smallest**
of the three bands: `A_valley` is a fifth the size of `A_Soret`, so it reaches 0.005/min while the Soret is
still shedding 0.010/min — **twice as much absorbance per minute, and invisible to the gate.**

⇒ **the gate's quantity is right (turbidity) and its units are wrong.** A rate threshold on an absorbance
must be **relative**, or it is a threshold on the dilution.

### ⛔⛔ 33.5 · AND `dQ%/dt ≈ 0` PROVES NOTHING — it is the read rule's own construction

Split `dQ%/dt` into its two terms (`Q% = −100·(A_v − A_Q)/A_S`), at the read row:

```
run                    numerator term   denominator term      sum    measured
BillaClever 001              -0.2096          +0.2116       +0.0020   +0.0020
Lugitsch 004                 -0.1439          +0.1451       +0.0012   +0.0012
Lugitsch 005                 -0.1851          +0.1996       +0.0145   +0.0142
Lugitsch 002                 -0.0730          +0.0755       +0.0026   +0.0025
Lugitsch 006                 -0.1123          +0.1036       -0.0087   -0.0086
```

⭐⭐⭐ **The two terms are 50–100× the residue and they cancel.** On 001 each side is moving at 0.21 Q% per
minute and the answer sits still at 0.002. ⇒ *"`Q%` has stopped changing"* is **not** evidence that the fill
has stopped clearing; it is evidence that `V` is doing exactly what it was designed to do — **be invariant
to what clearing does to the spectrum** (`DOC_metric_algebra.md`, the dilution-invariance proof).

⛔⛔ **The metric's greatest virtue is precisely what disqualifies it as the settling detector.** A quantity
built to ignore multiplicative changes in `A` cannot be used to decide when multiplicative changes in `A`
have finished. ⚠ §2.1 chose `A_valley` over `Q%` for the gate on **dose** grounds; **this is the deeper
reason, and it was never written down.**

⚠ It also means §32.6's plan to watch `Q%` values is only half right: **Edwin's instinct to look at `Q%`
was correct as a diagnosis** — the disagreements are visible there — **and wrong as a detector.**

### ⚠ 33.6 · A THIRD FINDING, FREE FROM THE SAME SPECTRA — the reference drifts, and NOT uniformly

The three runs' `REFERENCE` captures, 20:50 / 21:12 / 21:32, over 42 minutes:

| band | 001 → 003 |
|---|---|
| Soret 448–460 | **−2.1 %** |
| valley 500–560 | **−5.6 %** |
| Q 565–580 | **−8.9 %** |

⭐ §17/D4 (*"the reference ages while the sample settles"*) is **confirmed and quantified for the first
time**, and the drift is **wavelength-dependent — the red end falls four times faster than the blue.**
⇒ a single scalar reference-drift correction would be wrong.

Within a run the sample is captured *after* the reference, so the drift **inflates A**. On 001 (13.5 min
between them) that is +0.0029 / +0.0079 / +0.0126 in Soret / valley / Q:

```
001 as reported                19.863
001 with the drift removed     19.434     <- moves it FURTHER from 002 and 003
```

⭐ ⇒ **reference drift is a real, sizeable error and it is NOT the explanation for §33.3's disagreement** —
removing it makes the disagreement worse. Recorded here so nobody spends an evening on that hypothesis.
⚠ The lamp is not the only candidate (the reference jar was re-seated between runs); **separating lamp drift
from re-seating needs the null-run design of §16.26, not this data.**

### ⭐⭐ 33.7 · WHAT CHANGES

⛔ **C4 (κ) is withdrawn.** §32.10's five-jar session is **not** cancelled — it becomes the experiment that
measures *whether turbidity has a correctable spectral signature at all* — but nothing κ-shaped goes near an
answer.

⭐ **C1 (ceiling) and C2 (hunt window) stand unchanged.** They fix a read that reported the dark floor;
nothing in this section touches them, and they are still the only two changes that are safe to build today.

Three new ones, in confidence order:

#### ⭐⭐ C5 — the gate's threshold becomes **relative**, and it watches **A_Soret**

```
today   |dA_valley/dt| < 0.005 /min                    absolute, on the smallest band
C5      |dA/dt| / A     < theta_rel   for A_Soret AND A_valley, both
```

- ⭐ `A_Soret` is the largest band (best SNR) and the concentration carrier; `A_valley` stays because it is
  the most turbidity-sensitive. **Both must be flat**, which is what would have caught 001.
- ⭐ Relative units make the threshold **dilution-free** — today's 0.005 means something different for every
  dilution, which is a bug nobody had named.
- ⛔ **`theta_rel` IS NOT DERIVABLE FROM THE ARCHIVE.** At the read the twelve runs span 0.24–1.50 %/min in
  the Soret; any threshold under 1.5 %/min lengthens **almost every run**, and there is no cluster gap to
  plant it in (unlike `depthThreshold`, §29.2). ⇒ it must come from §33.8, and until then C5 is **recorded
  in the record, not enforced in the gate** (see C7).
- ⛔ ⚠ **AND IT MAY NEVER TERMINATE.** §1's whole premise is that clearing and browning fight; a fill whose
  Soret is still falling at 1 %/min after 25 minutes gets **no answer** under C5. ⭐ That is the honest
  outcome, and §33.8 is what tells us how often it happens.

#### ⭐⭐ C6 — the answer carries the **residual turbidity**, once history can supply "clear"

`A_Soret` at the read minus the stock's clear `A_Soret` is a *number*, not a judgement — but it needs a
per-stock clear value, which is `SPEC_history_tracker.md`'s job. ⇒ **C6 is the first concrete thing the
history tracker would buy**, and it turns every archived answer into something correctable rather than
something suspect.

#### ⭐⭐ C7 — until C5 and C6 exist, **the run must say what it was doing when it stopped** *(build this now)*

All three band rates are already computed every row. Cost: three numbers in `MonitorRecord` and one line on
the report.

```
001  read at t = 807.6 s -- still clearing: A_Soret -1.06 %/min, A_valley -3.04 %/min, A_Q -1.85 %/min
```

⭐ That one line would have told Edwin not to trust 19.867 **on the evening he measured it**, without any
new physics, any new threshold, or any new experiment. ⛔ **It is the highest value-per-line change in this
whole section and it depends on nothing.**

### ⭐⭐ 33.8 · THE EXPERIMENT — ONE FILL, DRIVEN TO ACTUAL COMPLETION *(it has never been done)*

Every number in the archive comes from a run that stopped when a threshold fired. **Nobody has ever watched
a fill until it stopped changing.** Until that exists there is no "clear", no `theta_rel`, and no way to
grade any answer.

- **one jar of one stock**, DIAGNOSTIC mode, **60–90 minutes**, cap raised, no promotion.
- record the three band rates every row; ⭐ the question is simply **does `A_Soret` flatten, when, and at
  what value** — and what `Q%` reads there.
- ⭐⭐ **run a second jar of the same stock with the lamp shuttered between looks** (manual is fine — the
  operator blocks the beam between windows). ⚠ Without it, "the Soret never flattens" is unattributable
  between clearing that has not finished and browning that has started. §16.36 says both are real; **this
  pair separates them, and no run so far can.**

| result | consequence |
|---|---|
| `A_Soret` flattens, lit and shuttered arms agree | ⭐ clearing genuinely completes ⇒ `theta_rel` is derivable, C5 ships, and "clear" is defined per stock |
| flattens only in the shuttered arm | ⛔ the lamp is what prevents settling ⇒ **the shutter stops being an optimisation and becomes a prerequisite** (§29.4 argued for it; this would decide it) |
| flattens in neither | ⛔⛔ no fill in isopropanol ever settles ⇒ **the whole wait-for-settling protocol is unreachable**, and `SPEC_capture_quality.md` §16.12.7's hydrocarbon route is not an improvement but the only route |

⚠ **Pre-register the reading before the run**, per §16.34.3. ⭐ Note the third row: this experiment can
falsify §1 itself, which is why it precedes every remaining item in this spec.

### ⛔ 33.9 · WHAT §33 DOES NOT CLAIM

- ⛔ **It does not say the three answers are useless.** It says none of them is a *settled* measurement, and
  that the spread between two fills of one stock — **1.12 units, 18 floors** — is the honest size of the
  error the protocol currently carries. ⚠ That number is one pair; it is not σ_fill.
- ⛔ **It does not explain the turbidity term.** Neither λ⁻ⁿ nor grey fits (§33.3). **We do not have a model,
  and C6 deliberately reports a raw excess rather than pretending to one.**
- ⛔ **It does not touch C1 or C2**, which fix a different defect (a read on the dark floor) and remain the
  only buildable items.
- ⚠ **`theta_rel`, "clear", and the shutter question are all one experiment away**, and that experiment is
  one jar and one evening (§33.8).

---

## ⭐⭐⭐ 34 · THE BLACK BOX — Edwin's fixed-time protocol, and the correction it forces on §33  *(Edwin, 2026-08-19; DESIGN, not built)*

> ⭐ Edwin: *"think we should measure always for 20 minutes and take where Q changes the least … what is
> astounding: 001 and 003 would end at about the same 20.0 … view it as a black box: same recipe, same
> parameters (maybe also hidden ones), same outcome — that would help from a pragmatic point."*
>
> ⛔⛔ **He is right about 20.0, and being right about it refutes a conclusion §33 drew.** That correction
> comes first, because everything else in this section follows from it.

### ⛔⛔ 34.1 · THE CORRECTION TO §33 — 001 lands on the clear run's number, so its turbidity excess did not hurt it

```
001   last five looks   19.870  19.867  19.889  19.867  19.873    slope +0.0013 /min   SETTLED at 19.87
003   last five looks   20.471  20.409  20.349  20.317  20.310    slope -0.1296 /min   still FALLING
      003 extrapolated  +2 min -> 19.995      +5 min -> 19.568
```

⭐⭐ **Two preparations, one number: 19.87 and 19.99.** Edwin's "about 20.0" for both, and 003 reaches it in
**two more minutes** of a run that had already gone 13.9.

⛔ §33.2 concluded that 001 was *"read carrying the same residual turbidity as the fill he called wrong"*,
because both sat at ≈ +32 % `A_Soret` above 003's clear value. **The outcome refutes the inference:**

| | `A_Soret` excess | Q% | agrees with the clear run? |
|---|---|---|---|
| 001 | **+32 %** | 19.867 | ⭐ **yes**, to 0.13 |
| 002 | **+31 %** | 20.990 | ⛔ **no**, by 1.00 |

⇒ **`A_Soret` excess does not predict the error in `Q%`.** Two fills with the same excess land 1.12 apart.
⭐⭐ **`V` is far more robust to ordinary residual haze than §33 credited** — which is what it was designed
for — and **the outlier is 002, not 001.** §33.2 and §33.3 are corrected here: the finding is not *"all
three were contaminated"*, it is *"two normal preparations agree and the warm-bath one does not."*

⚠ What survives from §33 unchanged: §33.4 (the gate watches one band's absolute rate), §33.5 (`dQ%/dt ≈ 0`
is the read rule's own construction), §33.6 (the reference drifts wavelength-dependently). ⛔ What does not:
the framing that every archived answer is turbidity-contaminated in proportion to its Soret excess.

### ⭐⭐ 34.2 · SO WHAT DID THE WARM BATH DO? — it is a *preparation* fault, not a *reading* fault

At **the same `A_Soret`** the two fills differ only in the green:

| | `A_Soret` | `A_valley` | `A_Q` | Q% |
|---|---|---|---|---|
| 001 — prepared, inserted, waited | 0.9631 | **0.1289** | 0.3202 | 19.867 |
| 002 — warm-bath treated | 0.9586 | **0.2076** (+61 %) | 0.4082 | 20.990 |

⭐ Edwin's glyceride remark is the mechanism that fits: **the bath melts the higher-melting glyceride/wax
fraction; on the way into a cooler holder it comes back out of solution as a fine dispersion** that (a)
scatters in the green, (b) does **not** settle — 002's `A_valley` moved 1.6 % in 98 s — and (c) keeps
growing, which is why 002's `Q%` **rose** at 11σ instead of falling.

⇒ ⭐⭐ **PRAGMATIC VERDICT, and it is the cheapest result of the session: do not warm-bath.** Prepare the
dilution, insert it, wait. That is 001's recipe, it produced the archive's only clean Billa settle, and it
is exactly Edwin's black-box proposal.

⚠ One fill, one mechanism, no repeat. It should be checked by making the bath the *only* difference between
two fills of one stock — but the direction of the evidence is not ambiguous.

### ⭐ 34.3 · WHAT `A_valley` IS, IN NUMBERS  *(Edwin: "don't know how to interpret the A_valley values")*

`A_valley` = mean absorbance over **500–560 nm**, the *clarity floor*: the window where pumpkin-oil pigment
absorbs **least**, sitting between the Soret band (blue) and the Q band (green-yellow). Almost everything
measured there is **turbidity**, plus a small pigment tail. ⇒ it is the instrument's cloudiness gauge, and
its units are absorbance, so it scales with dilution.

| `A_valley` | what it means, on this rig |
|---|---|
| **0.06 – 0.10** | clear — the whole Lugitsch archive, and 003's endpoint |
| **0.13** | 001 at its read: ⭐ visually clear, still ~2× the clear floor |
| **0.20** | 002's plateau: hazy, and it never moved |
| **0.7** | 001 on insertion: cloudy |
| **2.7** | 003 on insertion: **opaque** — 0.1 % of the light gets through, below one sensor code (§32.4) |

The three runs, in one line each — and the decision notes are in the record even though the report does not
print them (⭐ that is itself a fault worth fixing):

```
001  A_valley 0.691 -> 0.128 over 13.8 min, monotone      "788.7s gate fired (was clearing) - waiting one row for the vertex"
                                                          "807.6s gate fired (still clearing) - the minimum is still the newest look"
                                                          "826.3s settled - read as a parabola vertex"
002  A_valley 0.208 -> 0.204 over 1.6 min, FLAT           "98.5s gate fired - settled - no turning point deeper than 0.126,
                                                           so the FIRST look is the answer"
003  A_valley 2.667 -> 0.059 over 13.9 min, -98 %         "835.8s gate fired - settled - no turning point deeper than 0.126,
                                                           so the FIRST look is the answer"        <- the §32.2 defect
```

### ⚠ 34.4 · THE TIMING COINCIDENCE — real, and it belongs to the **gate**, not to the fill

⭐ Edwin: *"interesting that 001 and 003 stop at nearly the same time though their Q% curves differ."*
Measured, and it is closer than "nearly":

```
001  gate at 826.3 s        starting A_valley 0.691
003  gate at 835.8 s        starting A_valley 2.667      3.86x more turbidity, 9.5 s later = 1.1 %
```

⚠ **But it is not evidence of a fixed physical clock.** A shared-τ exponential predicts the cloudier fill
gates `τ·ln(3.86)` later — **+243 s at τ = 3 min, +567 s at τ = 7 min**. It gated **+9.5 s** later. And the
two fills were **not** doing the same thing at that moment:

| at t = 825 s | relative rate of `A_valley` | absolute rate |
|---|---|---|
| 001 | **−3.0 %/min** | −0.0039 /min |
| 003 | **−8.0 %/min** | −0.0046 /min |

⇒ ⭐⭐ **the two runs stopped together because `θ` is an ABSOLUTE threshold and their absolute rates happened
to cross it together, while their relative rates differ by 2.6×.** Under §33.4's relative gate they would
have stopped far apart — 003 much later, which is what it needed.

⚠ ⇒ the coincidence is **not** support for a physical 14-minute constant. ⭐ It **is** a small piece of
support for a *fixed-duration protocol*: nothing about these two fills demanded different treatment.

### ⭐⭐ 34.5 · EDWIN'S RULE, TESTED — "run 20 min, take the window where Q% changes least"

Applied to all twelve archived runs, at window sizes m = 4 / 6 / 8 rows:

| run | flattest window | its Q% | recorded answer | verdict |
|---|---|---|---|---|
| **BillaClever 001** | t ≈ 780 s, slope +0.0001 /min | **19.874** | 19.866 | ⭐ **reproduces it to 0.008** |
| Lugitsch 002 / 004 / 005 / 006 / 007 | late, slope < 0.05 /min | 13.47 – 14.17 | same ± 0.03 | ⭐ agrees |
| 20260818A/001 | t ≈ 207 s, slope +0.0002 /min | 28.419 | 28.321 | ⭐ agrees |
| 20260819/001 (TEST C) | t ≈ 192 s | 13.481 | 13.585 | ⭐ agrees |
| BillaClever 002 | t ≈ 52 s, slope **+0.109 /min** | 21.086 | 20.990 | ⚠ no flat window exists |
| **BillaClever 003** | t ≈ 501 s, slope +0.008 /min | ⛔ **21.197** | 8.450 | ⛔ **picks the wrong plateau** |

⛔ **On 003 the rule lands on a false shoulder.** Between t = 473 s and t = 567 s the `Q%` curve genuinely
flattens at ≈ 21.2 on its way down, and that shoulder is flatter than anything else in the 13.9 minutes the
run lasted.

⭐⭐ **BUT THAT IS NOT A REFUTATION, IT IS THE PREMISE BEING MISSING: not one run in the archive lasted 20
minutes.** The longest is 13.9. Edwin's rule asks for a duration no run has ever been given, and on 003 the
final plateau — the one the rule is meant to find — begins roughly where the data stop.

#### ⭐⭐ The fix costs nothing: take the **LAST** flat window, not the **flattest**

Scan backwards from the end and take the first window whose `Q%` slope is flat within noise. On the archive
this is decisive:

| run | last window flat? | answer |
|---|---|---|
| BillaClever 001 | ⭐ yes, +0.0013 /min | **19.87** ✅ |
| BillaClever 003 (as run, 13.9 min) | ⛔ no, −0.130 /min | **no answer — "still falling"** ✅ correct |
| BillaClever 002 | ⛔ no, +0.109 /min | **no answer — "still rising"** ✅ correct |
| Lugitsch 003 | ⛔ no, +0.318 /min | no answer ⭐ — and §29.1 already named this run's read the worst of its series |
| Lugitsch 002 / 004 / 006, 20260818A | ⭐ yes | unchanged |

⭐⭐ **It answers the one fill that settled and refuses the three that did not** — including 003, whose
shoulder it now walks straight past. ⛔ The 21.2 trap only exists for a rule that ranks windows by flatness;
a rule that reads *the last* flat one cannot fall into it.

⚠ "Flat within noise" needs a number, and it is derivable rather than chosen: the residual scatter of `Q%`
inside a window is **0.009 – 0.037**, so a slope is resolvable to ≈ 0.01 /min. ⭐ Set the threshold from
**what the answer would still move over the remainder of the protocol** — at 0.01 /min over a final 5
minutes that is 0.05, under one instrument floor. ⇒ `|slope| < 0.01 /min` **and** not significant at 2σ.

### ⭐⭐⭐ 34.6 · THE ARGUMENT FOR THE FIXED PROTOCOL THAT NEITHER OF US MADE — it deletes a σ_fill term

§2.4 of this spec says, in its own words:

> *"Damage accumulates while the fill clears, and clearing time varies between fills … at the measured +1.0
> to +1.6 `Q%` per hour, [the damage term varies with it]."*

⭐⭐ **A fixed duration turns that variable into a constant.** Every fill receives the **same dose**, so
photodamage stops being a per-fill error and becomes a **common offset** — which cancels in every comparison
the product actually makes (oil vs oil, batch vs batch, this month vs last). ⛔ Today the archive's runs
range from **98 s to 836 s of lamp**, an 8.5× spread in dose, and §2.4 counts that spread as noise.

⭐ It also retires §2.1's objection. §2.1 rejected gating on `Q%` because it *"works and costs ten minutes of
light"*. **Under a fixed duration the light is already paid for**, so the objection has nothing left to
object to — and `Q%`, the quantity we actually report, becomes the quantity we judge.

### ⭐⭐ 34.7 · THE PROPOSAL — the protocol replaces most of the machine

| | |
|---|---|
| **P1** | ⭐ **Fixed run duration**, default **20 min**, a setting rather than a constant. **No gate.** |
| **P2** | ⭐ **Read = the LAST window flat within noise** (§34.5). No flat window ⇒ **no answer**, and the record says which way it was still moving and how fast. |
| **P3** | ⭐ **Keep C1** (the absorbance ceiling, §32.7). A dark-floor row is not a look under any protocol. |
| **P4** | ⭐ **Keep C7** (all three band rates in the record, §33.7). It is the honesty line, and it costs nothing. |
| **P5** | ⭐ **Protocol rule: no warm bath** (§34.2). |

⭐⭐ **And note what it DELETES:** `THETA_PER_MINUTE`, `GATE_SPAN_SECONDS`, `GATE_CONSECUTIVE`,
`__hasFallenSinceMaximum`, the depth discriminator and `depthThreshold`, the vertex read, C2's hunt window,
C5's relative gate — **the entire gate-and-branch apparatus of §14, §29, §30 and §32.7.** TEST B and TEST C
survive only as *diagnostics* (a re-clouding or ripening fill still needs to be named), not as terminators.

⚠ That is a large deletion and it should feel uncomfortable. ⭐ The case for it is that **every defect found
in §32 and §33 lives in the deleted part**, and the part that keeps working — the metric, the ring buffer,
the record, the report — is untouched.

### ⚠ 34.8 · WHAT IT COSTS, AND WHERE IT CAN STILL GO WRONG

1. ⛔ **002 under a 20-minute protocol is unknown, and it is the case that could look bad.** It was rising
   at 0.109 /min with no sign of stopping; extrapolated blindly it reaches ≈ 23 by minute 20. ⭐ P2 refuses
   it either way — *no flat window, no answer* — so the protocol is safe, but **we still do not know what a
   warm-bath fill does over 20 minutes**, and P5 exists so we do not have to find out.
2. ⚠ **20 minutes is a protocol constant, not a law, and it is oil-dependent.** **5 of 7 Lugitsch fills
   arrived clear** and settled in 105 s; **0 of 3 Billa fills did.** The one Lugitsch fill that had to clear
   did 92 % of its haze in **314 s**; Billa 001 did 81 % in **826 s** — ⭐ consistent with Edwin's glyceride
   reading, and it means 20 min is generous for Lugitsch and may be **tight for a worse oil**. ⇒ P1 makes it
   a setting, and §34.9 measures it.
3. ⚠ **20 minutes of dose on every fill, including the ones that were ready in 105 s.** At the measured
   browning rates that is 0.02–0.11 `Q%`/min of damage banked. ⭐ P2 mitigates it — the read is the last
   *flat* window, so a fill that starts browning has no flat window late and gets refused rather than
   silently over-baked. ⛔ But it is a real cost, and it is the strongest argument for the shutter (§29.4).
4. ⚠ **A false plateau longer than the window can still fool P2.** 003's shoulder was ~95 s of genuine
   flatness. ⭐ Requiring the flat window to be the last one, *and* to be followed by nothing, is what makes
   this safe — so the protocol must never stop early "because it looks flat". **Run the full 20 minutes,
   always.** That is Edwin's rule and it is load-bearing.

### ⭐⭐ 34.9 · THE EXPERIMENT — unchanged in substance, cheaper in form

§33.8 asked for one fill driven to completion. ⭐ **It is now simply the protocol run long:** one Billa fill,
prepared 001's way, **60 minutes**, DIAGNOSTIC, no promotion — plus **a second jar with the lamp shuttered
between looks**.

Three questions, one session:

| question | what the run answers |
|---|---|
| **is 20 minutes enough?** | when does the last flat window first appear — and does it appear at all |
| **where does it land?** | ⭐ does the flat value agree with 19.87 / 19.99, which would confirm §34.1 outright |
| **is the lamp the limit?** | the shuttered arm separates "still clearing" from "already browning" (§16.36) |

⭐ **And it is now falsifiable in Edwin's own terms:** if a 60-minute run of a fresh 001-style prep lands on
**20.0**, the black-box claim — *same recipe, same parameters, same outcome* — is established for this oil,
and the fixed protocol can ship without any of the deleted machinery.

### ⛔ 34.10 · WHAT §34 DOES NOT CLAIM

- ⛔ **It does not prove 20 minutes is the right number.** It shows no run has ever tested it and gives the
  one session that would.
- ⛔ **It does not establish the glyceride mechanism.** It is the best fit to 002's behaviour and to the
  Lugitsch/Billa clearing-speed gap; it is not measured.
- ⛔ **It does not retract §33.4 or §33.5.** The gate really does watch one band's absolute rate, and
  `dQ%/dt ≈ 0` really is the read rule's own construction — ⭐ which is precisely why P1/P2 delete the gate
  instead of repairing it.
- ⚠ **It rests on one pair.** 001 and 003 agreeing at ≈ 20.0 is two fills of one stock on one evening. ⭐ It
  is enough to change the design; it is not enough to close it, and §34.9 is one evening away.

---

## ⭐⭐ 35 · THE REPEATABILITY SERIES — Edwin's "make some other 001-like measurements"  *(2026-08-19; DESIGN, not built)*

> ⭐ Edwin: *"think I should make some other 001-like measurement and look if it gives the same result — can
> then repeat this with the same oil — and could repeat the same lab recipe (no waterbath, which introduces
> other artefacts maybe and is uncontrollable in some way). BTW the metric itself says the oil is a brown
> one. At least this is correct."*

### ⭐⭐ 35.1 · THE VERDICT CHECK FIRST — and the domain guard saved a false GREEN

`V_THRESHOLD = −18.6` (**higher `Q%` = browner**), `V_VERDICT_BAND = (12.0, 22.0)`, scored corpus corridor
12.70–20.82.

| candidate answer for these fills | verdict | margin above the 18.6 line |
|---|---|---|
| 001 as reported — **19.87** | 🟤 **brown** | +1.27 = **20 floors** |
| 003 extrapolated — **19.99** | 🟤 brown | +1.39 = 22 floors |
| 003 last row — **20.31** | 🟤 brown | +1.71 = 27 floors |
| 002 as reported — **20.99** | 🟤 brown ⚠ past the scored corridor (20.82), inside the band | +2.39 = 38 floors |
| §34.5's false shoulder — 21.20 | 🟤 brown | +2.60 |
| ⛔ 003 as reported — **8.45** | **NO VERDICT** | — |

⭐⭐ **Every candidate answer except the broken one gives the same verdict.** The entire §32–§34 argument
moves the number by ~1 unit; the sample sits **20 to 38 instrument floors** on the brown side of the line.
⇒ **for this oil, none of the read-rule work changes a decision.** It matters for samples near 18.6, and
that is the honest scope of it.

⭐⭐⭐ **AND THE 8.450 DID NOT PRODUCE A WRONG VERDICT — IT PRODUCED NONE.** The report for run 003 carries
**no `Verdict · Q%` item at all**, because 8.45 falls below `V_VERDICT_BAND`'s floor of 12.0 and §3.1a
withholds rather than clamps. ⇒ **a guard written for out-of-domain *samples* caught an out-of-domain
*read*, and the false GREEN that 8.45 would otherwise have drawn never reached paper.**

⚠ **Do not conclude the defect is harmless.** The guard caught 8.45 because it was catastrophic. A dark-floor
read that lands at 13 or 17 sits comfortably inside the band and would print a confident GREEN. ⭐ C1 (§32.7)
is still required; §3.1a is a backstop that happened to be in the right place, not a fix.

⚠ Lugitsch A reads 13.5–14.5 ⇒ **green**, Billa Clever ≈ 20 ⇒ **brown**: a class gap of ≈ 6 `Q%` units
against a disputed precision of ≈ 1. ⭐ Edwin's *"at least this is correct"* is the standing sanity check,
and it should be **written into every session**: if the verdict ever disagrees with what the oil looks like
in the jar, stop and find out why before trusting any number that evening.

### ⭐⭐ 35.2 · WHY THE REPEAT SERIES IS THE RIGHT NEXT MOVE

Everything §32–§34 concluded rests on **one evening and three fills**, two of which were deliberately
abnormal (a warm bath, a fridge-clouding). ⭐ Edwin's proposal removes exactly that weakness: **repeat the
one recipe that worked, several times, and see whether the black box returns the same number.** No new
physics is needed to make it informative, and it is the only experiment that can *establish* the pragmatic
claim rather than argue it.

⛔ **And the warm bath is out on his own grounds** — *"uncontrollable in some way"*. §34.2 says the same
thing from the data: it changes `A_valley` by +61 % at unchanged `A_Soret` and leaves a dispersion that does
not settle. ⇒ **the bath is not a faster route to the same state; it is a different state.**

### ⭐⭐ 35.3 · THE SERIES, IN ORDER — and the order is load-bearing

⛔ **Do the long run FIRST.** Repeating at 20 minutes before knowing whether 20 minutes is enough would
produce five numbers that agree with each other and mean nothing.

| | what | how long | why |
|---|---|---|---|
| **T0** | ⭐ **one fill, 60 min**, DIAGNOSTIC, no promotion *(= §34.9)* | 60 min | when does the last flat window first appear? does it appear at all? does it land on ≈ 20.0? |
| **T0b** | ⭐ **second fill, 60 min, lamp SHUTTERED between looks** (operator blocks the beam by hand) | 60 min | separates *still clearing* from *already browning* — the one thing no run can currently do |
| **T1** | ⭐⭐ **five fills, same stock, same recipe, no bath**, at the duration T0 says | 5 × ~20 min | **σ_fill** — the number the whole product rests on |
| **T2** | ⚠ **another day: a FRESH dilution from the same bottle, three fills** | 3 × ~20 min | separates σ_fill from **σ_prep** — is the dilution or the fill the variable? |

⚠ T0 + T0b is one evening; T1 is a second; T2 is a third. ⭐ T0 alone already answers the question that
blocks the fixed protocol, so **it is worth doing even if the rest slips.**

### ⭐⭐ 35.4 · THE READING, FIXED BEFORE THE RUN  *(§16.34.3's habit)*

The archive's own benchmark: **Lugitsch A, seven fills, one session — mean 13.997, sd 0.377.** That is
today's σ_fill, and it is what T1 must be judged against.

| T1 result | verdict |
|---|---|
| **sd ≤ 0.20** across five fills | ⭐⭐ the black box holds and is **better** than Lugitsch A ⇒ the fixed protocol ships, and the whole §14/§29/§30 gate apparatus is deleted (§34.7) |
| **sd 0.20 – 0.40** | ⭐ the black box holds at today's known repeatability ⇒ the protocol ships; σ_fill stays the dominant error and the shutter becomes the next target |
| **sd > 0.50** | ⛔ a hidden parameter is not controlled ⇒ **do not ship the protocol**; the next job is to find the variable, and §35.5's log is where it will be |
| any fill lands **> 1.0** from the others | ⛔ treat it as a 002 — look for what was different about that fill before averaging it in |

⭐ Second reading, free: **does the mean land on 19.9 – 20.0?** If it does, §34.1's *"001 and 003 agree"* is
confirmed on five fills instead of two, and the black-box claim is established for this oil.

### ⭐ 35.5 · THE HIDDEN PARAMETERS — write them down, because that is what "same parameters" means

⭐ Edwin's *"maybe also hidden ones"* is the whole risk of the black-box argument: it holds only if the
things nobody recorded really were the same. **Per fill:**

- **room temperature**, and the **holder** temperature if a thermometer is to hand
- ⭐ **lamp warm-up** — minutes the lamp had been on before the reference capture *(§14.5a already asks for
  a pre-warmed instrument; this is where it gets checked)*
- ⭐ **time from prep to insertion**, in minutes — the fill ages before it is measured
- **stock age** (when the dilution was made), and whether the stock was **shaken** before the pour
- **which pour** of the stock (§33 showed "first 4 ml" and "second 4 ml" are not automatically alike)
- **jar identity** — the same physical jar, or a different one
- ⚠ and, per §33.6, **when the reference was captured relative to the sample**

⭐ ⚠ One deliberate control worth adding at no cost: **vary the prep-to-insertion time on purpose across the
five fills** (say 2, 5, 10, 20, 40 minutes). If σ_fill is dominated by fill *age*, that shows up as a trend
rather than as scatter — and a trend is diagnosable where scatter is not.

### ⭐ 35.6 · TWO THINGS THE SERIES BUYS BEYOND THE ANSWER

1. ⭐ **A re-seat check, for one jar, for free.** After the last fill's run, lift the jar out, re-seat it,
   and read 3 more minutes. Memory of §16.26 says **jar re-seating is the whole archive's CV**; this is the
   cheapest possible confirmation, and it comes at the end where the extra dose can no longer contaminate a
   fresh answer.
2. ⭐ **The first real test of C7** (§33.7 — the three band rates on the record). Five runs of one recipe
   should show the *same* band rates at the read. If they do not, the rates are the diagnostic that says
   which fill was different — which is precisely the "hidden parameter" detector §35.5 asks for.

### ⛔ 35.7 · WHAT THE SERIES CANNOT DO

- ⛔ **It cannot validate the metric**, only its repeatability. Five fills agreeing on 19.9 says the
  instrument is consistent; it does not say 19.9 is the right description of the oil.
- ⛔ **It cannot separate σ_fill from lamp drift** within a session — §33.6 measured the reference moving
  −2.1 % / −5.6 % / −8.9 % across 42 minutes, and a five-fill series spans ~2 hours. ⭐ **Capture a fresh
  reference for every fill** (already the protocol) and record the reference band means, so the drift is at
  least visible in the record rather than folded into σ_fill.
- ⚠ **It cannot settle the 20-minute constant for other oils.** Lugitsch fills mostly arrive clear; Billa
  never does. The number is per-oil until a second oil has been through the same series.

---

## ⭐⭐⭐ 36 · RUNS 004 AND 005 — the pour is a real variable, the black box works, and §34 must be walked back  *(Edwin, 2026-08-19; DESIGN, not built)*

> ⭐ **004** — new dilution **R**, the *first 4 ml*, no water bath. **005** — the same dilution, the *other
> 4 ml*, no water bath. Both `SETTLED_AFTER_CLEARING`, both read as a VERTEX, both textbook.
>
> ⛔⛔ **Two of §34's conclusions are wrong and are retracted below.** They were drawn from an archive that
> contained no clean V-shaped Billa run; 004 and 005 are two, and they refute the retracted parts directly.

### ⭐⭐⭐ 36.1 · THE HEADLINE — the best repeatability the archive has ever produced

| stock | run | pour | treatment | answer |
|---|---|---|---|---|
| 1 (A/B) | 001 | **first 4 ml** | none | **19.866** |
| 1 (A/B) | 003 | second 4 ml | fridge-clouded | **20.310** |
| 1 (A/B) | 002 | second 4 ml | ⛔ warm bath | 20.990 |
| 2 (R) | **004** | **first 4 ml** | none | **19.431** |
| 2 (R) | **005** | second 4 ml | none | **20.234** |

```
first  pours   19.866  19.431      spread 0.435
second pours   20.310  20.234      spread 0.076   <- 1.2 instrument floors, across TWO SEPARATE DILUTIONS
```

⭐⭐ **Two independently prepared stocks, same recipe, same pour position, agree to 0.076.** Against the
Lugitsch A benchmark of **sd 0.377** over seven fills of one dilution, that is the best number this
instrument has ever produced — and it is σ_prep + σ_fill combined, not σ_fill alone.

⇒ ⭐⭐⭐ **Edwin's black box holds. Same recipe, same parameters, same outcome — measured, not argued.**

### ⭐⭐ 36.2 · THE POUR IS A REAL VARIABLE, AND IT CLOSES §33.3's UNEXPLAINED GAP

```
within stock 1:   001 -> 003    +0.444        (first -> second pour)
within stock 2:   004 -> 005    +0.803        (first -> second pour)
                                -------
                  mean          +0.623        SAME SIGN IN BOTH STOCKS
warm bath, same pour, same stock:  003 -> 002   +0.680
```

⭐⭐ **§33.3's "1.124 apart and no correction can explain it" now decomposes exactly:** 001 → 002 is a pour
step (+0.444) *plus* a bath step (+0.680). ⭐ The pour term is **independently reproduced in stock 2**, in
the same direction and of the same order — which is what turns it from arithmetic into a finding.

⚠ **The second pour reads BROWNER.** The obvious reading is that the first 4 ml is supernatant and the
second drags the heavier, settled fraction — but ⛔ **it is confounded with two other things**: the second
pour is always measured *later* (18–22 min), so it is also the *older stock*, and it is also a later point
on the lamp's evening. §36.6 says how to break the confound in one session.

⇒ ⭐ **Until it is broken, the pour is part of the recipe.** Two fills are comparable only if they came from
the same pour position. §35.5 already asked for "which pour" in the log; this promotes it from a nice-to-have
to a **required field**.

### ⛔⛔ 36.3 · RETRACTION 1 — §34.7's "delete the gate apparatus" is WRONG

004 and 005 are exactly the case the vertex machinery was built for, and it handled both correctly:

| run | Q% minimum | position | rise after it | vertex read | run length |
|---|---|---|---|---|---|
| 004 | 19.436 at t = 232 s | **row 13 of 32** | **+0.234** | **19.431** ✅ | 9.8 min |
| 005 | 20.236 at t = 537 s | **row 30 of 49** | **+0.280** | **20.234** ✅ | 14.9 min |

⭐⭐ **Clean V-shapes with an interior minimum and a genuine browning limb after it — and `__read`'s
"argmin interior ⇒ VERTEX" branch read both of them right.** §34.7 proposed deleting `depthThreshold`, the
vertex read and the whole §14/§29/§30 branch structure on the strength of an archive that happened to
contain no such run. ⛔ **That proposal is withdrawn.**

⭐ The defects found in §32/§33 are **narrower** than §34 claimed:

- **003** — a dark-floor read. Fixed by **C1** (the absorbance ceiling), which stands.
- **002** — a fill that never cleared. Needs a **verdict**, not a different read (C3), which stands.
- **everything else in the archive** — the machinery works.

### ⛔⛔ 36.4 · RETRACTION 2 — §34.5's "take the LAST flat window" is worse than what it replaced, and it did not even fix its own test case

Replayed over all fourteen runs, against Edwin's original *flattest* window:

| run | Edwin: **flattest** | mine: **last flat** | recorded (vertex) | truth |
|---|---|---|---|---|
| 004 | 19.454 ⭐ | 19.458 ⭐ | **19.431** | ~19.44 |
| **005** | 20.457 ⛔ **+0.22** | 20.457 ⛔ **+0.22** | **20.234** | ~20.24 |
| **003** | 21.197 ⛔ | 21.197 ⛔ **— unchanged!** | 8.450 ⛔ | ~20.0 |
| Lugitsch 001 / 003 / 005 / 006 / 007 | 13.5 – 14.2 ⭐ | ⛔ **REFUSED** ×5 | 13.5 – 14.5 | — |

⛔ **My modification refuses five archived runs that were fine**, lands 0.22 high on 005 — it settles on the
*browning plateau*, which on 005 is flatter than the minimum region — and ⛔⛔ **leaves 003 at 21.197, the
exact failure it was invented to fix.** It was wrong on its own terms and I did not check it against a
V-shaped run because none existed.

⚠ **Edwin's original rule is the better of the two**, but it is not right either: it also takes 005's
browning plateau (20.457), because a curve that has finished browning is genuinely flat.

⭐⭐ **What actually separates them is what comes AFTER the flat part** — a rise. `__read`'s existing
"argmin must be interior" test asks precisely that, and it is why the vertex read beat both window rules on
005. ⇒ **the minimum, confirmed by a rise, is the right rule. Keep it.**

### ⭐⭐ 36.5 · WHAT EDWIN'S 20 MINUTES *IS* RIGHT FOR — guaranteeing the rise has time to appear

The one place the fixed duration is clearly load-bearing:

| run | minimum at | run length | rows after the minimum |
|---|---|---|---|
| 004 | **3.9 min** | 9.8 min | 19 ⭐ well confirmed |
| 005 | **9.0 min** | 14.9 min | 19 ⭐ well confirmed |
| 001 | **13.5 min** | 13.8 min | ⚠ **1** — rise of +0.006, barely interior |

⭐⭐ **001's run outlasted its own minimum by a single row.** Its answer is right, and it is right by
9.5 seconds. A run one row shorter would have hit *"the minimum is still the newest look — waiting for its
far side"* and ended with **no value**.

⇒ ⭐ **Fixed 20 minutes, kept from §34, for a reason §34 did not give:** not to replace the minimum rule but
to guarantee it can be *confirmed*. The three minima land at 3.9 / 9.0 / 13.5 min; 20 min covers all three
with margin, 15 min would have been marginal for 001.

⭐ And §34.6's argument survives untouched: a fixed duration makes the dose equal across fills, which
deletes §2.4's varying-clearing-time term from σ_fill. ⚠ With one addition — the read is the *minimum*, not
the last look, so the extra minutes cost lamp without touching the answer. **That is the price of confirming
the minimum, and 004/005 show it is worth paying.**

### ⚠ 36.6 · CORRECTION TO §33.6 — it is a WARM-UP TRANSIENT, not a linear drift, and the first run of the evening is the outlier

With five references instead of three, over 149 minutes instead of 42:

| run | clock | min | Soret | valley | Q |
|---|---|---|---|---|---|
| 001 | 20:50 | 0 | 128.83 | **148.37** | **70.10** |
| 002 | 21:12 | 22 | 126.80 | 141.41 (−4.7 %) | 65.36 (−6.8 %) |
| 003 | 21:32 | 42 | 126.16 | 140.00 (−5.6 %) | 63.89 (−8.9 %) |
| 004 | 23:01 | 131 | 128.45 | 142.79 (−3.8 %) | 66.33 (−5.4 %) |
| 005 | 23:19 | 149 | 129.56 | 141.89 (−4.4 %) | 65.03 (−7.2 %) |

⛔ **There is no linear trend** (fits give r = −0.37 to +0.53). **001's reference is simply 5–9 % brighter in
the red than every later one, and 002–005 agree to ~1.5 %.** ⇒ what §33.6 read as a drift rate is a
**warm-up transient in the first twenty minutes of the evening**, followed by a stable lamp.

⭐ **§14.5a's "pre-warm the instrument" now has a number**: the first run of an evening carries a reference
up to 9 % off in the red, and **run 001 spans the transient** — its reference at 20:50, its answer 13.5 min
later. ⇒ ⚠ **001 is the least trustworthy of the three unbathed runs**, which is a reason to weight
**004 → 005 (+0.803, both well after warm-up)** above 001 → 003 (+0.444) for the pour term.

⭐ And the drift *correction* on the answers is small, not the 0.43 §33.6 implied:

```
001  -0.060      002  -0.001      003  -0.000      004  -0.016      005  -0.041
```

⇒ ⛔ **§33.6's "reference drift is a real, sizeable error" is withdrawn as stated.** The real rule is simpler
and cheaper: **pre-warm, and discard or flag the first run of the evening.**

### ⭐ 36.7 · THE PROTOCOL, AS IT NOW STANDS

| | |
|---|---|
| **P1** | ⭐ Fixed run duration, **20 min** — so the browning limb always has time to confirm the minimum (§36.5) |
| **P2** | ⛔ ~~read the last flat window~~ → ⭐ **keep the existing read: the Q% minimum, confirmed by an interior argmin, read as a vertex** (§36.4) |
| **P3** | ⭐ Keep **C1**, the absorbance ceiling (§32.7) — still required for 003 |
| **P4** | ⭐ Keep **C7**, the three band rates in the record (§33.7) |
| **P5** | ⭐ **No warm bath** (§34.2) — the bath term is +0.680 |
| **P6** | ⭐⭐ **NEW — record the pour position, and compare only like with like** (§36.2). The pour term is +0.44 to +0.80, larger than everything else on this list. |
| **P7** | ⭐⭐ **NEW — pre-warm the lamp, and flag the first run of the evening** (§36.6) |

⭐ Note what is **no longer** on the list: the deletion of the gate apparatus, the last-flat-window read, the
κ correction, and the relative-rate gate C5 — ⚠ C5 is not withdrawn, but 004 and 005 show the current gate
producing correct answers, so it drops from "required" to "revisit after §35's T1".

### ⭐⭐ 36.8 · THE NEXT SESSION — one change to §35, and it breaks the pour confound

§35's T1 (five fills, one stock) is still the right series. ⭐ **Add one thing that costs nothing:**

> **Pour BOTH aliquots at the same moment, and measure them in the OPPOSITE order on alternate stocks.**

| what follows the effect | what it is |
|---|---|
| the **pour position** (first vs second), regardless of order measured | ⭐ real stratification in the jar — the second pour carries the heavier fraction |
| the **measurement order** (whatever runs second) | ⚠ stock ageing, or the lamp's evening — and then §36.2's finding is not about pouring at all |

⭐ Two stocks, four runs, one evening, and it settles a **+0.6 to +0.8 term** — larger than σ_fill, larger
than the drift, and second only to the warm bath among everything measured so far.

⚠ And keep §35.4's reading unchanged: five fills, sd ≤ 0.20 ⇒ ship; > 0.50 ⇒ a hidden parameter is loose.
⭐ The 0.076 agreement of §36.1 says the ≤ 0.20 outcome is plausible — **from two fills, which is not a
repeatability measurement.**

### ⛔ 36.9 · WHAT §36 DOES NOT CLAIM

- ⛔ **0.076 is two numbers.** It is the most encouraging result in the file and it is not σ_fill. §35's T1
  is still owed.
- ⛔ **The pour mechanism is not established** — stratification, stock age and lamp evening are confounded
  (§36.8).
- ⛔ **It does not rescue 003 or 002.** C1 and C3 are still required; 004 and 005 simply show that the rest of
  the machine was never broken.
- ⭐ **And it does not change the verdict:** 19.431 and 20.234 are both **brown**, 13 and 26 instrument
  floors above the 18.6 line (§35.1).

---

## ⭐⭐ 37 · THE DESK LIGHT, THE FRIDGE, AND WHETHER THREE RUNS SEED THE HISTORY TRACKER  *(Edwin, 2026-08-19; DESIGN, not built)*

### ⭐⭐ 37.1 · THE DESK LIGHT — tested against each run's own browning track, and it explains 15 % of the gap

⭐ Edwin: *"the 'other 4 ml' were sitting on my desk before some monitor and some light … but the light is
low (very low) compared with the lamp."*

⭐⭐ **This is testable without any new run**, because every run traces its own photodamage track: along the
browning limb, `A_Soret` falls and `Q%` rises, and the slope of that track says what a given amount of
bleaching costs in `Q%`.

```
004 browning limb (20 rows)   A_Soret 1.0123 -> 0.9281 (-8.3 %)   Q% 19.436 -> 19.669 (+0.234)
                              slope  dQ%/dA_Soret = -2.211
005 browning limb (20 rows)   A_Soret 0.9571 -> 0.8812 (-7.9 %)   Q% 20.236 -> 20.440 (+0.204)
                              slope  dQ%/dA_Soret = -3.402
```

If 005 were simply *"004, further browned by the desk"*, it must sit on 004's own track:

```
004 answer 19.431 at A_Soret 1.0123
005        measured at A_Soret 0.9571      (dA_Soret -0.0552)
   predicted by pure browning:  19.553
   MEASURED:                    20.234
   ------------------------------------
   SHORTFALL:                   +0.681     <- 85 % of the +0.803 gap is NOT photodamage
```

⇒ ⭐⭐ **Edwin's own caveat is confirmed by the data: the desk light cannot account for it.** It buys about
0.12 of 0.80. ⚠ The test assumes desk-light browning follows the same `(A_Soret, Q%)` track as lamp browning
— a different spectrum could bleach differently — but a **5.7× shortfall** is not a marginal miss.

⭐ It is still worth removing: **keep both aliquots in the dark** costs nothing and deletes a term. §37.5's
design does that anyway.

### ⭐ 37.2 · TEMPERATURE ON THE WAY IN IS **NOT** A PROBLEM — Edwin is right, and the numbers are stronger than he claimed

⭐ Edwin: *"the one that was put in the fridge also gave a good value — so temperature of the solution as it
is input into the spectrometer seems to be NO real problem, as the spectrometer's warming settles it."*

Run **003** went in cold and opaque (`A_valley` 2.667, 0.1 % transmission) and:

| | terminal `A_valley` |
|---|---|
| 003 — **from the fridge** | **0.0586** ⭐ the **lowest of all five** |
| 005 | 0.1209 |
| 001 | 0.1279 |
| 004 | 0.1406 |
| 002 — warm bath | 0.2042 |

⭐⭐ **The cold fill did not merely recover — it ended the clearest of the evening**, and its `Q%` (20.310)
agrees with the other second aliquot (20.234) to **0.076**. ⇒ the lamp's warming fully resolves cold-induced
haze, and does so *more* completely than it resolves native haze.

⚠ **One confound, named:** 003 was also the more dilute aliquot of stock 1 (`A_Soret` 0.7312 against 001's
0.9599), so it had less material to hold in suspension. ⭐ The conclusion — *cold in is recoverable* — does
not depend on it; the "clearest of all" ranking does.

⛔ **The cost is time, not accuracy:** 003 needed 13.9 minutes and had not finished. ⇒ **a cold fill is
acceptable and slow**, which under §36.5's fixed 20-minute protocol costs nothing at all.

### ⛔ 37.3 · THE WARM BATH IS DEAD — agreed, and the epitaph is three numbers

| | |
|---|---|
| **+0.680** | the bath's own bias, same stock, same aliquot (003 → 002) |
| **1.6 %** | how much its `A_valley` fell in 98 s — it does not settle at all |
| **+0.109 /min at 11σ** | its `Q%` was still *rising* when the instrument answered |

⇒ ⭐ **P5 stands: no warm bath.** It is not a faster route to the settled state; it is a different, unstable
state that the instrument cannot recognise as bad.

### ⛔⛔ 37.4 · THREE RUNS DO **NOT** SEED THE HISTORY TRACKER — and the reason is worse than the count

⭐ Edwin: *"taking 001, 004 and 005 — do you think that this would suffice for the history tracker?"*

`SPEC_history_tracker.md`'s alarm is the SNV shape distance `D = √(1 − r²)`. Computed on the **promoted
capture** of each run, over 460–630 nm:

```
          001      004      005      002
 001   0.0000   0.1675   0.1576   0.1964
 004   0.1675   0.0000   0.0882   0.1150
 005   0.1576   0.0882   0.0000   0.0856
```

⛔⛔ **There is no separation at all.** The three *good* runs span D = 0.088 – 0.168; the distance from a good
run to **002 — the fill we know is bad** — is 0.086 – 0.196. **002 is closer in shape to 005 (0.086) than
001 is to 004 (0.168).** Separation factor **0.5×**: an alarm has nowhere to sit.

#### ⭐⭐ And the diagnosis is the useful part: `D` is measuring TURBIDITY, not chemistry

```
  correlation of D against |ΔA_valley| across the six pairs:   r = +0.835
```

⭐⭐ **The shape distance is a turbidity-difference detector.** ⚠ Removing a fitted linear baseline from each
spectrum does not rescue it (separation 0.35×) — the pedestal is not a straight line (§32.3, §33.3).

#### ⭐⭐⭐ WHY — and it is a consequence of this spec's own read rule

The answer is read at the `Q%` **minimum**, which is where clearing and browning *cross*. **That crossing
happens at a different turbidity for every fill:**

```
A_valley at the promoted capture   001 0.1289  004 0.1955  005 0.1716  006 0.1544  007 0.0921   sd 0.0398
A_valley at the LAST row           001 0.1279  004 0.1406  005 0.1209  006 0.1263  007 0.0915   sd 0.0182
   (updated 2026-08-20 to the five good Billa fills; the first cut of this table used four runs
    from before 006/007 existed and quoted ranges, not sd)
```

⇒ ⭐⭐ **the spectrum stored beside the answer is, by design, at an idiosyncratic clearing state.** That is
right for the verdict — `Q%` is what is comparable — and **wrong for shape tracking**, which needs spectra
taken in the same condition.

#### ⭐⭐ THE FIX, AND IT IS CHEAP

- ⭐ **Store the LAST row's spectrum as well as the answer's.** The last row is **2.2× more consistent** in
  turbidity across fills (sd 0.0182 against 0.0398) and is what the history tracker should compare.
  ⭐ Drawn out: `docs/figures/w5_two_spectra.png`.
  ⚠ §15.1 stores only the answer's spectrum; this adds one array per run.
- ⭐ **Or compare at a matched `A_valley`** — pick, from each run's ring, the row nearest a fixed turbidity.
  ⛔ Needs per-row spectra retained, which §9.1a's retention window does not currently guarantee.
- ⚠ Either way, **`SPEC_history_tracker.md` gains a second blocker beside dose**: the *clearing state* of the
  compared captures. It should be written there before the tracker is built.

#### ⭐ So how many runs would seed it?

⛔ **Unanswerable until the turbidity confound is removed** — with `D` dominated by clearing state, more runs
would only measure the clearing-state spread more precisely. ⭐ **Fix the compared quantity first, then three
to five runs of one recipe will tell you the floor.** Edwin's good feeling is about the *`Q%` repeatability*
(0.076 — genuinely excellent), and that feeling is justified; it just does not transfer to the shape metric.

### ⭐⭐ 37.5 · THE TWO MORE MEASUREMENTS — Edwin's count is right, and here is the design

⭐ Edwin: *"so you would need two more measurements I guess."* **Yes — two, on one new stock.** The existing
four runs are all *first-then-second*; two runs in the opposite order complete the square.

```
stock 3:  draw BOTH aliquots at the same moment, into two jars
          jar A = the FIRST 4 ml      jar B = the OTHER 4 ml
          both kept IN THE DARK from the moment they are drawn   (removes §37.1's term)
          measure jar B FIRST, then jar A                        (reverses the order)
```

| what the +0.6…+0.8 follows | conclusion |
|---|---|
| the **draw** (B still reads high even when measured first) | ⭐ real stratification in the vessel ⇒ P6 stands: pour position is part of the recipe |
| the **order** (whatever runs second reads high) | ⚠ it is ageing or the lamp's evening, **not** the pour ⇒ §36.2 is renamed and P6 is replaced by "measure within N minutes of drawing" |
| **nothing — the gap vanishes** | ⭐ it was the desk light after all, and §37.1's browning-track test is wrong about the mechanism ⇒ the fix is "keep aliquots dark", which is free |

⚠ **Two runs distinguish the three outcomes but cannot size the effect.** ⭐ They are worth doing first
anyway: all three answers change what §35's five-fill T1 has to control for, and T1 is the expensive session.

### ⭐ 37.6 · THE LEDGER, AS IT STANDS TONIGHT

| term | size | status |
|---|---|---|
| the **warm bath** | +0.680 | ⛔ **dead** — P5, do not use it |
| the **aliquot / pour** | +0.44 … +0.80 | ⚠ **real, mechanism open** — §37.5 settles it in two runs |
| **desk light on the waiting aliquot** | ≈ +0.12 of it | ⚠ small; removed for free by keeping aliquots dark |
| **cold fill (fridge)** | ≈ 0 in `Q%`, +14 min in time | ⭐ **not a problem** — Edwin is right, and 20 min absorbs it |
| **first run of the evening** (warm-up) | reference 5–9 % off in the red | ⚠ flag or discard it — P7 |
| **σ (prep + fill), like-for-like** | **0.076** on two runs | ⭐ excellent, and it is two runs — T1 still owed |
| **reference "drift"** | −0.001 … −0.060 on the answers | ⭐ small; it was a warm-up transient, not drift (§36.6) |
| **history-tracker shape distance** | no separation (0.5×) | ⛔ **blocked** on the clearing-state confound (§37.4) |

### ⛔⛔ 37.7 · CORRECTION TO §37.4 — THE HISTORY TRACKER IS **NOT** BLOCKED. I USED THE WRONG CONTROL.  *(Edwin: "why is the history tracker dead or 'blocked on clearing state'?", 2026-08-19)*

⛔ **§37.4's conclusion is withdrawn.** It rested on a category error and on a correlation measured over six
pairs of one oil.

#### ⛔ The category error

I used **002 as the "known bad" negative control**. 002 is **the same oil, from the same stock** — badly
*prepared*, not chemically different. ⇒ **a shape alarm is supposed to be blind to it.** "D fails to separate
002 from the good runs" was never evidence that D is broken; if anything it is evidence that D is doing its
job, since the oil did not change.

#### ⭐⭐ The test that actually answers the question — and D passes it cleanly

Same `D = √(1 − r²)`, same 460–630 nm window, but asking **does it separate DIFFERENT OILS while staying
small WITHIN one oil?**

| comparison | pairs | min | median | max |
|---|---|---|---|---|
| **within** Lugitsch A (7 fills, one oil) | 21 | 0.0454 | **0.1043** | 0.1982 |
| **within** Billa, the three good runs | 3 | 0.0882 | 0.1576 | 0.1675 |
| **within** Billa, including the bath fill 002 | 6 | 0.0856 | 0.1363 | 0.1964 |
| ⭐⭐ **between** Lugitsch and Billa — *different oils* | 21 | **0.3375** | **0.3844** | 0.4755 |

```
worst within-oil  0.1982        best between-oil  0.3375        NO OVERLAP,  1.70x on the worst case
median within     0.104         median between    0.384                     3.7x on the medians
```

⭐⭐⭐ **D separates the two oils with no overlap across 45 pairs.** The history tracker's own quantity works.

#### ⭐ And the turbidity correlation does not survive a wider test

```
Billa, 6 pairs, A_valley spanning 0.129 - 0.208    r(D, |dA_valley|) = +0.835
Lugitsch, 21 pairs, A_valley spanning 0.072 - 0.105  r(D, |dA_valley|) = +0.073
```

⇒ ⚠ **the turbidity term is real but small, and it only shows up when fills clear to widely different
states.** Lugitsch's fills arrive clear and land in a narrow band, and there `D` does not track turbidity at
all. §37.4's `r = +0.835` was **six pairs of the one oil whose fills happen to be most unevenly cleared** —
it was a finding about the Billa set, not about the metric.

#### ⭐ What survives from §37.4, correctly scoped

1. ⭐ **Residual turbidity inflates the WITHIN-oil floor** — Billa's median 0.158 against Lugitsch's 0.104,
   and Billa's fills spread 0.129–0.196 in `A_valley` against Lugitsch's 0.072–0.105. **It costs sensitivity,
   not correctness.**
2. ⭐ **Storing the LAST row's spectrum beside the answer's is still worth doing** (§37.4's fix), because the
   last row's turbidity spread is 4× tighter. ⚠ It is an **optimisation now, not a prerequisite.**
3. ⭐ **The warm-up run inflates D too:** 001's two pairs are the highest in the Billa set (0.158, 0.168)
   while 004–005 is the lowest (0.088) — consistent with §36.6's finding that 001's reference is 5–9 % off
   in the red. ⇒ **another reason for P7 (flag the first run of the evening)**, and it applies to shapes as
   well as to numbers.

### ⭐⭐ 37.8 · SO: DO 001, 004 AND 005 SEED IT? — yes, at the minimum the tracker's own rule allows

`SPEC_history_tracker.md` already requires **reference = mean of ≥ 3 fills (5 comfortable)**, and says the
tracker must draw no band and announce *"reference still forming"* below that. Three fills is therefore
exactly the floor, not a shortcut.

⛔ **The one thing three fills cannot give you is the alarm THRESHOLD.** Three fills make three pairs, and a
spread from three numbers is not a spread. ⭐ **But it does not have to come from Billa:**

```
pooled within-oil floor, 24 pairs across two oils:   max 0.198
best between-oil distance, 21 pairs:                 min 0.338
                                                     -> a threshold at ~0.25 has margin on both sides
```

⭐⭐ **Take the alarm threshold from the pooled within-oil floor and the reference mean from the three Billa
fills.** That is buildable today.

⚠ Three caveats, all of them cheap to respect:

- ⭐ **Announce n.** With n = 3 the reference is one bad fill away from being wrong — §11's own finding was
  that a single outlier chosen as the anchor throws the band 0.41 off centre.
- ⚠ **Drop or flag 001** if a fourth good fill exists: it is the warm-up run, and it contributes the two
  widest pairs in the set.
- ⚠ **The threshold is provisional on two oils.** 0.25 sits in a gap measured between Lugitsch and Billa;
  a third oil could land closer, and the standing rule stays *compare verdicts, never numbers*.

⇒ ⭐ **Edwin's good feeling was right on both halves after all** — the scalar side (σ 0.076 like-for-like)
and the shape side (1.70× worst-case separation). §37.4 said otherwise because it tested the metric against
a bad *fill* instead of a different *oil*.

### ⭐⭐ 37.9 · HOW SENSITIVE IS THE SHAPE ALARM, AND DOES IT DEPEND ON OTHER OILS?  *(Edwin, 2026-08-19)*

#### ⭐⭐⭐ `D` and `Q%` carry nearly the same information — 55 pairs, r = +0.972

```
D = 0.0494 * |dQ%| + 0.0897            r = +0.972 over 55 pairs, two oils

|dQ%| 0 - 1   n=25   D median 0.104        <- the noise floor: a 1-unit change is invisible
|dQ%| 1 - 3   n= 2   D median 0.156
|dQ%| 3 - 6   n=14   D median 0.374
|dQ%| 6 - 8   n=14   D median 0.410
```

| | resolves | |
|---|---|---|
| the **scalar** tracker (`Q%`) | **0.076** | like-for-like, §36.1 |
| the **shape** alarm at D = 0.25 | **≈ 3.2 `Q%` units** | |
| the within-oil floor D = 0.198 | ≈ 2.2 `Q%` units | |

⭐⭐ **The scalar tracker is ~40× the more sensitive of the two, and `D` is very largely a noisier restatement
of it.** ⇒ **the shape half is NOT an independent second opinion on drift.**

⚠ That is not an argument against building it — it is an argument for **what to build it for**. `D`'s job is
the *categorical* question: **is this even the same kind of oil?** (a different pressing, a different
supplier, adulteration — something that moves the spectrum's shape without necessarily moving `Q%`).
⛔ Nothing in the archive contains such a sample, so **D's value against the case it is actually for remains
unmeasured**; what §37.7 proved is that it separates two genuinely different oils, which is the weakest
version of that claim.

⇒ ⭐ **Build the scalar tracker for drift. Keep D as the categorical check, and say so in its own spec, or it
will be read as a sensitive alarm that it is not.**

#### ⭐ The pour is a SCALAR effect, not a shape effect

```
004 vs 005   different pours, dQ% = 0.803   ->  D = 0.0882   <- the TIGHTEST Billa pair
001 vs 004   same pour,       dQ% = 0.435   ->  D = 0.1675
001 vs 005   different pours, dQ% = 0.368   ->  D = 0.1576
```

⭐ The two widest Billa pairs are the two that involve **001, the warm-up run** (§36.6). The pour, which moves
`Q%` by 0.80, barely moves the shape at all. ⇒ **P6 (record the pour) is a scalar-tracker concern; P7 (flag
the first run of the evening) is a shape-tracker concern.**

#### ⭐⭐ Does buildability depend on other oils behaving like Billa? — only if the threshold is SHARED

| threshold design | depends on other oils? |
|---|---|
| ⚠ **shared** — one number (≈ 0.25) for every oil | ⭐ **yes.** It assumes every oil's within-oil floor stays under ~0.2. An oil whose fills clear as unevenly as Billa's, or worse, raises its own floor and starts false-alarming. |
| ⭐⭐ **per-oil** — each oil's threshold from its OWN reference fills | ⛔ **no.** Nothing about oil B can invalidate oil A's alarm. |

⇒ ⭐⭐ **Recommend per-oil thresholds.** The tracker already stores ≥ 3 reference fills per oil; the floor
comes from the same fills at no extra cost, and the shared 0.25 becomes only the **fallback for an oil that
does not yet have enough fills of its own**.

⚠ With n = 3 a per-oil floor is poorly determined (3 pairs). ⭐ Use the pooled 0.25 until an oil reaches
**five** fills, then switch it to its own — which is exactly `SPEC_history_tracker.md`'s existing "≥3, 5
comfortable" ladder, now with a reason attached to each rung.

#### ⭐ What one more Billa fill tonight would buy

| what it gives | |
|---|---|
| ⭐ a **fourth** good fill, so **001 can be dropped** | 001 is the warm-up run and contributes both widest pairs (0.158, 0.168) |
| ⭐ the first true **σ_fill within one stock** on this oil | 004 and 005 are different pours, so the archive still has **no Billa replicate** |
| ⚠ what it does NOT give | a third draw from the same vessel is a *third pour* — confounded again (§36.2) |

⇒ ⭐ **A fresh stock, single first-pour fill, measured straight away** is the clean version, and the lamp is
already warm at that hour, which removes P7's term for free.

---

## ⭐⭐ 38 · RUNS 006 AND 007 — one exemplary run, one compromised one, and a bias §2.2 claimed to have cured  *(2026-08-20, runs of 2026-08-19 night)*

### ⭐ 38.1 · 007 is the best-behaved run the instrument has produced

Monotone from 20.705, gate at 384.5 s, then **five consecutive rows of *"the minimum is still the newest
look — waiting for its far side"*** before settling at 501.0 s. Answer **19.573**; its own settled plateau is
19.613 — **0.040 apart.** It also reached the **lowest turbidity of any Billa fill** (`A_valley` 0.0915,
`A_Soret` 0.8173).

⭐ The "wait for the far side" rule doing exactly its job, five times in a row, is worth recording: that is
§30.14's read behaving as designed on a real fill.

### ⛔⛔ 38.2 · 006's answer is read off a NOISY EXCURSION, and it is 0.884 low

```
   local residual scatter about a 5-row line, run 006
     t   0-150 s   n= 8   sd 0.4777
     t 150-260 s   n= 6   sd 0.2749      <- the vertex was read here, at t = 225.5, Q% 19.004
     t 260-400 s   n= 8   sd 0.2325
     t 400-660 s   n=14   sd 0.0143      <- the run's own noise floor, 20x quieter
```

The Q% trace through the excursion: `20.128 · 19.780 · 20.146 · 19.465 · 19.004 · 19.192 · 19.347 · 19.656 ·
19.985 · 20.115` — then it comes **back to trend** and holds 19.86–19.89 for fifteen rows.

```
   006 answer (vertex)      18.989
   006 settled plateau      19.873
   ------------------------ -0.884
```

⛔ **That is not a browning limb, it is a bounce.** The curve dips 0.9, returns, and then behaves. The vertex
read the bottom of the dip. ⚠ Something disturbed the fill through the first four minutes and the record
does not say what; `A_valley` also stalls there (0.2051 → 0.1961 → 0.1959) before resuming its fall.

### ⭐⭐⭐ 38.3 · AND IT IS NOT AN ISOLATED CASE — the vertex is below the plateau on EVERY run

| run | vertex | settled plateau | difference | end slope |
|---|---|---|---|---|
| 001 | 19.866 | 19.878 | −0.012 | −0.009 /min |
| 007 | 19.573 | 19.613 | −0.040 | −0.038 /min |
| 004 | 19.431 | 19.578 | **−0.147** | +0.076 /min |
| 005 | 20.234 | 20.468 | **−0.235** | +0.013 /min |
| **006** | 18.989 | 19.873 | ⛔ **−0.884** | +0.007 /min |

⛔⛔ **§2.2's premise does not hold as written.** It says: *"The minimum of n noisy samples is biased low by
~0.9 sd because it selects the most negative excursion. A parabola through the three samples around it
averages instead of selecting."* ⭐ **The parabola is fitted AROUND THE SELECTED MINIMUM — so the selection
happens first, and the fit inherits it.** Averaging three points reduces the variance of the estimate; it
does not undo the choice of *which* three.

⚠ **Two of the five differences are legitimate** — 004 and 005 are browning after their minimum (+0.076 and
+0.013 /min), so their plateau really is more damaged than their minimum, and the vertex is right to sit
below it. ⛔ **006 is not**: its plateau is flat (+0.007 /min) and its dip was noise.

⇒ ⭐ **The instrument cannot presently tell "genuinely least-damaged" from "noise dip", and 006 is the first
run where the difference is large enough to be unmissable.**

#### ⭐ Candidate guards, none of them yet chosen

- ⭐⭐ **Local-scatter admissibility.** Compute the residual scatter around the candidate minimum and compare
  it with the run's own tail scatter. 006: **0.275 against 0.014 — 20×.** A minimum found in a stretch that
  noisy is not a measurement. ⚠ Needs a factor, and the archive can supply one: the other four runs' minima
  sit in stretches within ~2× of their tails.
- ⭐ **Require the rise after the minimum to be SUSTAINED.** 004, 005 and 007 rise monotonically to the end;
  006 rises 1.11 and then falls back. A browning limb does not come back down. ⚠ Cheap, and it needs the
  full 20 minutes to be visible — another argument for P1.
- ⚠ **Refuse a vertex more than X below the settled plateau** — ⛔ would also flag 005, whose 0.235 is real
  browning. Not usable alone.

### ⛔ 38.4 · SO STOCK 3 CANNOT SETTLE ORDER-vs-POUR — the two reads disagree in SIGN

```
using the VERTEX answers    006 18.989 -> 007 19.573   = +0.584
using the settled PLATEAUS  006 19.873 -> 007 19.613   = -0.260
```

⛔ **Opposite signs.** With 006 compromised, the pair cannot decide anything, and §37.5's experiment is
**not yet done** — it needs repeating with two clean runs.

### ⚠ 38.5 · AND I NEED ONE FACT FROM EDWIN BEFORE EVEN THE SIGN MEANS ANYTHING

**Which aliquot was 006 and which was 007?** §37.5 asked for the *second* aliquot to be measured *first*. If
that swap happened the interpretation inverts, and I cannot read it off the data.

⭐ The one hint the data give — in both earlier stocks the **second aliquot was the more dilute** one:

| | first-measured ends `A_Soret` | second-measured ends | |
|---|---|---|---|
| stock 1 | 001 0.9599 | 003 0.7312 | −23.8 % |
| stock 2 | 004 0.9281 | 005 0.8812 | −5.1 % |
| **stock 3** | **006 0.8762** | **007 0.8173** | **−6.7 %** |

⇒ ⚠ **by that signature 007 looks like the second aliquot, i.e. the swap did not happen** — but that is an
inference from n = 2, not a record. **Please say which was which.**

### ⚠ 38.6 · SOFTENING §36.6 — the reference WANDERS, it is not a one-way warm-up

With seven references instead of five (reference band means, 500–560 nm):

```
001 148.4   002 141.4   003 140.0   004 142.8   005 141.9   006 147.8   007 144.7
```

⛔ **006 is back up near 001's level.** So the pattern is not "high at the start, then stable" — it is a
**±3 % wander over the evening with no trend**, range 140.0–148.4. ⭐ That is much more consistent with
**re-seating the reference jar for every run** (`SPEC_capture_quality.md` §16.26: *jar reseating = the whole
archive CV*) than with a lamp warm-up.

⇒ ⚠ **§36.6's "warm-up transient" is downgraded to "001 sat at one end of the wander".** ⭐ **P7 survives but
changes meaning:** not *"discard the first run"* but *"record the reference band means every run, and treat
a run whose reference sits at the edge of the spread as suspect."* ⚠ Still worth pre-warming; just not for
the reason §36.6 gave.

### ⭐ 38.7 · SHAPE DISTANCES WITH FIVE BILLA FILLS — still separating, with a thinner margin

```
          001      004      005      006      007
 001   0.0000   0.1675   0.1576   0.1812   0.1378
 004   0.1675   0.0000   0.0882   0.0670   0.2219
 005   0.1576   0.0882   0.1314   0.0000   0.2312
 006   0.1812   0.0670   0.1314   0.0000   0.2161
 007   0.1378   0.2219   0.2312   0.2161   0.0000
```

| | n | min | median | max |
|---|---|---|---|---|
| within Billa (5 fills) | 10 | 0.0670 | 0.1625 | **0.2312** |
| Lugitsch vs Billa | 35 | **0.3375** | 0.3844 | — |

⭐ **Still no overlap — but the separation falls from 1.70× to 1.46×**, and §37.8's proposed threshold of
0.25 now sits only 0.019 above the worst within-oil pair. ⛔ **0.25 is too tight. Use 0.28–0.30**, or better,
the per-oil rule of §37.9.

⭐⭐ And the outlier is instructive: **007 is far from everything (0.216–0.231) and it is the CLEAREST fill**
(`A_valley` 0.0915 against the others' 0.121–0.141). ⇒ **the turbidity term in `D` is confirmed a third
time**, and §37.4's fix — comparing spectra at a matched clearing state — moves back up the list from
"optional" to "worth doing before the tracker ships".

---

## ⭐⭐⭐ 39 · THE SWAP HAPPENED — it is not the pour, not the order, it is **LIGHT ON THE WAITING ALIQUOT**  *(Edwin confirmed the assignment, 2026-08-20)*

> ⭐ **006 was the second aliquot, 007 the first — the §37.5 swap happened**, both drawn at the same moment
> and both kept in the dark.
>
> ⛔⛔ **§36.2's "pour effect" is withdrawn, and so is §37.1's dismissal of the desk light.** Both were right
> about the number and wrong about the cause.

### ⭐⭐⭐ 39.1 · THE TEST — each pair compared at MATCHED turbidity, not at its own answer

Comparing the two aliquots at their own answers compares them at different clearing states (§37.4). Reading
each run's `Q%` at the **shallowest turbidity both members reached** removes that:

| pair | matched at `A_valley` | 1st aliquot | 2nd aliquot | 2nd − 1st |
|---|---|---|---|---|
| stock 1 — 001 / 003 | 0.1279 | 19.873 | 21.216 | ⛔ **+1.343** |
| stock 2 — 004 / 005 | 0.1406 | 19.669 | 20.411 | ⛔ **+0.742** |
| **stock 3 — 007 / 006** | 0.1263 | 19.912 | 19.886 | ⭐⭐ **−0.026** |

⭐⭐⭐ **The one pair drawn simultaneously and kept in the dark agrees to 0.026. The other two disagree by
0.74 and 1.34.**

### ⭐⭐ 39.2 · WHAT THAT ELIMINATES — three hypotheses, two die

| hypothesis | verdict |
|---|---|
| **the draw** (2nd aliquot carries a different fraction) | ⛔ **dead.** In stock 3 the 2nd aliquot reads the same as the 1st. And 007 is 6.7 % *more dilute* than 006 while reading the same `Q%` — a concentration difference with no `Q%` consequence, exactly as the metric's dilution-invariance requires. |
| **the measurement order** (whatever runs second reads high) | ⛔ **dead.** In stock 3 **006 ran first and 007 second**, and the gap is −0.026. Fifteen minutes of waiting, per se, costs nothing. |
| ⭐⭐ **light on the waiting aliquot** | ⭐ **the only one left standing.** Stocks 1 and 2: the waiting aliquot sat on the desk under a monitor. Stock 3: it waited **in the dark** — and the effect vanished. |

⇒ ⭐⭐⭐ **By elimination: Edwin's own throwaway remark — *"the 'other 4 ml' were sitting on my desk before some
monitor and some light"* — was the answer, and §37.1 dismissed it.**

### ⛔⛔ 39.3 · WHY §37.1's TEST SAID OTHERWISE, AND WHY IT WAS THE WRONG TEST

§37.1 predicted 005 from 004 along **004's own lamp-browning track** (`dQ%/dA_Soret`) and found a shortfall
of 0.681 — concluding the desk light explained only 15 %.

⛔ **The test assumed ambient browning follows the same spectral track as lamp browning. It does not, and it
has no reason to:**

- ⭐ the **lamp** illuminates a **narrow column** of the fill in a few specific bands; damage is confined to
  the beam path and reaches the rest only by convection
- ⭐ **ambient white light floods the whole 4 ml** from every direction, broadband

⇒ a weak omnidirectional source can deliver more dose *per unit volume* than a bright pencil beam, and it
bleaches a different mixture of chromophores. **The shortfall §37.1 measured is real — it is evidence that
the two photochemistries differ, not that the desk light is innocent.**

⚠ ⇒ **it cannot be calibrated out.** There is no conversion from lamp-dose to desk-dose. The only fix is the
procedural one, and it is free.

### ⭐⭐ 39.4 · THE ARCHIVE, RE-PARTITIONED — and it is the tightest set yet

| run | aliquot | what happened before it was measured | value | |
|---|---|---|---|---|
| 001 | 1st | measured first, no wait | 19.866 | ⭐ clean |
| 004 | 1st | measured first, no wait | 19.431 | ⭐ clean |
| 006 | 2nd | measured first, no wait *(dark design)* | **19.873** | ⭐ clean — **plateau**, its vertex is §38.2's noise dip |
| 007 | 1st | waited ~15 min **IN THE DARK** | 19.573 | ⭐ clean |
| 003 | 2nd | waited ~40 min **in light** (+ fridge) | 20.310 | ⛔ lit |
| 005 | 2nd | waited ~13 min **in light** | 20.234 | ⛔ lit |

```
CLEAN, n=4     mean 19.686   sd 0.220   range 0.442
LIT,   n=2     mean 20.272                        -> +0.586 above the clean mean
Lugitsch A benchmark, 7 fills                        sd 0.377
```

⭐⭐ **sd 0.220 over four fills, 1.7× tighter than the Lugitsch benchmark** — and that is across **three
separate dilutions**, so it is σ_prep + σ_fill together. ⚠ Four fills, and one of them (006) is rescued by a
plateau read rather than by the shipped rule.

### ⛔⛔ 39.5 · κ IS BURIED — the extrapolation makes things three times WORSE

Fitting each good run's own tail (`A_valley` ≤ 0.16) and extrapolating to zero turbidity:

```
run     slope        Q0(v=0)
001    +8.195         18.793
004   -12.036         21.329
005    -5.572         21.174
006    -3.076         20.277
007   +12.781         18.397
                      ------
       sd of Q0        1.346          vs  sd of the raw vertex answers  0.467
```

⛔ **The slopes do not even agree in sign.** §32.6's κ ≈ 4.5 was two runs that happened to line up; with five
runs the extrapolation triples the scatter. ⭐ **Withdrawn for good — do not revisit it.**

⚠ Note this does **not** contradict §39.1: comparing two runs *at the same turbidity* needs no model and
works; extrapolating one run *to zero turbidity* needs a slope, and the slope is not identifiable from a
tail where turbidity and dose move together (§32.6's caveat 1, now measured).

### ⭐⭐ 39.6 · WHAT CHANGES

| | |
|---|---|
| ⛔ **P6 withdrawn** | "record the pour position" — the pour has no effect. ⭐ Replace with: **P6′ — every aliquot stays in the dark from the moment it is drawn until it enters the holder.** Amber glass, a drawer, foil; anything. |
| ⭐ **P1, P3, P4, P5, P7 unchanged** | fixed 20 min · absorbance ceiling · band rates in the record · no warm bath · reference band means recorded |
| ⭐⭐ **P8 — NEW** | **compare fills at matched `A_valley`, not at their own answers**, whenever two runs are held against each other. §39.1 is the method; it turned a 0.74 disagreement into 0.026. |
| ⚠ **§38.2's noise-dip guard is now urgent** | 006 is in the clean set only because its plateau was used by hand. ⭐ Of the two candidates, **"the rise after the minimum must be sustained"** is the one that separates 006 from 004/005/007, and the fixed 20 minutes is what makes it observable. |

### ⭐ 39.7 · WHAT IS STILL OPEN

- ⚠ **The clean set is four fills, one of them hand-rescued.** §35's T1 is still owed, now with P6′ in force.
- ⚠ **How much light, for how long, matters?** Unmeasured. ⭐ Cheap to bound: draw three aliquots at once,
  measure one immediately, one after 15 min dark, one after 15 min on the desk. **One evening, and it turns
  §39.2's elimination into a measurement.**
- ⛔ **The lit runs are not recoverable.** No conversion exists (§39.3). 003 and 005 stay in the archive as
  *lit*, not as data about the oil.
- ⭐ **And the verdict never moved:** every one of the six is **brown**, 6 – 27 instrument floors above 18.6.

---

## ⭐⭐⭐ 40 · THE DRAWDOWN RULE — "a real minimum is one the curve never comes back down from"  *(Edwin's reading of run 006, 2026-08-20)*

> ⭐ Edwin, on the 006 plot: *"shouldn't we use the first minimum (1) after 'the answer'?"* — pointing at the
> shallow minimum at t ≈ 6.9 min, past the spurious dip the vertex read.
>
> ⭐⭐ **He is right, and formalising it gives a rule with a 14× cluster gap that reproduces every archived
> answer and repairs only run 006.**

### ⭐ 40.1 · What 006's curve actually does

```
Q%
22 |*
   |  * *  *
21 |       * * *  *                                the spurious excursion
20 |             * *  *  *      * * *              /
   |                    *  *  *       * * *_______________________ the browning limb
19 |                       (*)                     ^
   |                         "the answer" 19.004   (1) 19.782 at t=412.9
   +----|----|----|----|----|----|----|----|----|----|----
        0    2    4    6    8   10  minutes since insertion
```

The shipped read took the bottom of the dip (18.989). **After it the curve rises 1.11 and then falls 0.33
again** to Edwin's (1) at 19.782 — and from there it only ever goes up, to 19.886 at the gate.

### ⭐⭐⭐ 40.2 · THE RULE

```
candidate     = any interior local minimum of Q%
drawdown(i)   = the largest fall from a running maximum, over the rows AFTER i
tailSd        = residual scatter of the last 8 rows about a line   (the run's OWN noise floor)

ADMISSIBLE    iff  drawdown(i) <= G * tailSd
ANSWER        = the vertex around the DEEPEST admissible candidate
```

⭐ In one sentence: **a settling minimum is the point after which the curve only goes up. If it comes back
down, something other than browning was happening and it was not the minimum.**

### ⭐⭐ 40.3 · THE GAP IS 14×, AND THE THRESHOLD FALLS INSIDE IT

Every interior local minimum in run 006:

| t | Q% | drawdown after | ×tailSd (0.0084) | |
|---|---|---|---|---|
| 22.5 s | 21.066 | 2.0699 | 247 | ⛔ |
| 58.7 s | 20.758 | 1.8757 | 224 | ⛔ |
| 132.6 s | 20.046 | 1.1419 | 136 | ⛔ |
| 169.6 s | 19.780 | 1.1419 | 136 | ⛔ |
| **225.5 s** | **19.004** ← the shipped answer | 0.3329 | **39.8** | ⛔ |
| **412.9 s** | **19.782** ← ⭐ **Edwin's (1)** | 0.0212 | **2.5** | ⭐ admissible |
| 507.0 – 639.2 s | 19.849 – 19.876 | ≤ 0.0212 | ≤ 2.5 | admissible, shallower |

And across the whole archive:

```
legitimate minima, ten runs:   drawdown 0.0 - 2.8 x tailSd
run 006's spurious dip:                     39.8 x tailSd
                                            ------
                               a 14x gap. ANY G between 3 and 39 gives identical answers everywhere.
```

⭐⭐ **Derived, not chosen** — the same standard §29.2's `depthThreshold` was held to. **G = 10** sits at the
geometric centre.

### ⭐⭐ 40.4 · REPLAYED OVER THE ARCHIVE — it changes exactly one run

| run | rule | shipped | 2.0 raw min (vertex) | drawdown of that min | **drawdown rule, G = 10** | change |
|---|---|---|---|---|---|---|
| Lugitsch 001 | 1.0 | 14.459 | 14.428 | 0.0× | **14.428** | — unchanged |
| Lugitsch 002 | 1.0 | 13.476 | 13.467 | 1.7× | **13.467** | — unchanged |
| Lugitsch 003 | 1.0 | 14.246 | *no interior minimum* | — | *first-look branch* | — |
| Lugitsch 004 | 1.0 | 14.156 | 14.156 | 0.4× | **14.156** | — unchanged |
| Lugitsch 005 | 1.0 | 14.173 | 14.126 | 0.7× | **14.126** | — unchanged |
| Lugitsch 006 | 1.0 | 13.972 | 13.972 | 0.0× | **13.972** | — unchanged |
| Lugitsch 007 | 1.0 | 13.499 | 13.499 | 0.0× | **13.499** | — unchanged |
| 20260818A/001 | 2.0 | 28.321 | 28.321 | 0.0× | **28.321** | — unchanged |
| 20260819/001 | 2.0 | 13.585 | 13.471 | 0.5× | **13.471** | — unchanged |
| Billa 001 | 2.0 | 19.866 | 19.866 | 0.0× | **19.866** | — unchanged |
| Billa 002 | 2.0 | 20.990 | *no interior minimum* | — | *first-look branch* | ⚠ needs **C3** |
| **Billa 003** | 2.0 | ⛔ 8.450 | 21.015 | ⛔ **41.5×** | ⭐ **none admissible — NO ANSWER** | ⭐ **also caught** |
| Billa 004 | 2.0 | 19.431 | 19.431 | 1.4× | **19.431** | — unchanged |
| Billa 005 | 2.0 | 20.234 | 20.234 | 2.8× | **20.234** | — unchanged |
| **Billa 006** | 2.0 | ⛔ 18.989 | 18.989 | ⛔ **39.8×** | ⭐ **19.782** | **+0.793 REPAIRED** |
| Billa 007 | 2.0 | 19.573 | 19.573 | 0.0× | **19.573** | — unchanged |

⭐⭐ **A SECOND CATCH NOBODY ASKED FOR: run 003.** Its deepest interior minimum has a drawdown of 41.5×, so
**no candidate is admissible and the rule refuses to answer** — which is the correct ending for a fill that
never settled. ⇒ **§32.2's catastrophe is caught twice over**: by C1 (the absorbance ceiling, on the input
side) and independently by §40 (on the read side). ⚠ Run 002 still needs **C3**: a monotone rise has no
interior minimum at all, so it falls through to the first-look branch exactly as before.

⭐⭐⭐ **Ten runs bit-identical, one repaired.** Same property C1 and C2 have, and the reason to trust it.

### ⭐⭐ 40.5 · IT IS AN END-OF-RUN READ — WHICH IS WHY IT NEEDS EDWIN'S FIXED DURATION

⛔ `tailSd` and `drawdown` are both defined over **the rows after the candidate**, so neither exists until
the run is over. **The drawdown rule cannot drive a gate.**

⭐⭐ That is not a limitation, it is the **second independent argument for P1**: under a fixed 20-minute
protocol the run length is decided by the clock, the read happens once at the end, and the rule has all the
rows it needs. ⇒ **§34's fixed duration and §40's read rule are the same design arriving from two
directions** — Edwin proposed the first from a feeling and the second from a plot.

⚠ Two implementation notes:
- ⛔ **a candidate needs rows after it.** A minimum on the last row has `drawdown = 0` and would be trivially
  admissible — the existing *"the minimum is still the newest look, waiting for its far side"* guard must
  stay, or the last row always wins.
- ⚠ **`tailSd` assumes the tail is settled.** On a fill still clearing at the cap (003) the tail carries real
  slope; the residual-about-a-line form handles that, but the run should be reported as unsettled anyway
  (§33.7's band rates).

### ⭐ 40.6 · WHAT IT DOES TO THE CLEAN SET

```
006 = 18.989   shipped vertex (noise dip)     clean-4 mean 19.465   sd 0.365
006 = 19.873   plateau, taken by hand         clean-4 mean 19.686   sd 0.220
006 = 19.782   ⭐ Edwin's (1) / drawdown rule  clean-4 mean 19.663   sd 0.198
```

⭐⭐ **sd 0.198 over four fills of three separate dilutions** — better than my hand-picked plateau, and
**1.9× tighter than the Lugitsch benchmark of 0.377**. ⚠ And it is now produced by a *rule*, not by me
choosing a number off a chart, which is the part that matters.

### ⭐ 40.7 · IT REPLACES §38.3's OTHER CANDIDATES

- ⛔ **local-scatter admissibility** — tested, and it overshoots: at F = 3 or 5 it rejects Edwin's (1) too
  (its neighbourhood sits at 7.1× the tail) and lands on a noise wiggle further up the limb at 19.849. **The
  drawdown rule needs no window and no smoothing.**
- ⛔ **"vertex too far below the plateau"** — would also flag 005, whose 0.235 is real browning. Dead.
- ⭐ **"the rise must be sustained"** — this *is* that idea, made testable.

⇒ ⭐⭐ **§38.3's open guard is closed.** The read rule becomes: **vertex around the deepest local minimum
whose drawdown is within 10 × the run's own tail noise.**

---

## ⭐⭐ 41 · CURVATURE — Edwin's alternative, tested three ways  *(Edwin, 2026-08-20: "take the minima and take the one with the lowest curvature? or something like that")*

The intuition is sound and it is the right one: **a noise dip is a sharp V; a settling minimum is a broad
basin.** Three forms of it were tested; the third is the keeper.

### ⛔ 41.1 · FORM 1 — "the LOWEST curvature wins". Fails, and in a familiar way.

| run | lowest-curvature minimum | correct |
|---|---|---|
| Billa 005 | ⛔ 20.455 @ 798.8 s | 20.236 |
| Billa 006 | ⛔ 19.876 @ 639.2 s | 19.782 |
| Billa 004 | 19.451 @ 362.1 s | 19.436 |

⛔ **The flattest point on a curve that has finished browning is flatter than the minimum**, so the rule
drifts up the browning limb — **exactly §34.5's failure mode again** (the "flattest window" rule landing on
005's browning plateau). ⭐ Flatness alone always walks forward in time; it needs a depth criterion beside it.

### ⚠ 41.2 · FORM 2 — "the DEEPEST minimum whose curvature is below a cut". Works, with no margin.

At a cut of `a < 2.0 Q%/min²` **every one of the thirteen runs gives the right answer, including 006 →
19.782.** But:

```
largest curvature among the CORRECT minima :  +1.832   (20260818A/001)
curvature of 006's spurious star           :  +3.365
                                              ------
                                              gap 1.8x
```

⛔ **A 1.8× gap is not a place to plant a threshold** — the drawdown rule's is 14.2×. At a cut of 5.0 run 006
reverts to 18.989.

#### ⛔⛔ And raw curvature is CADENCE-DEPENDENT, which disqualifies it outright

A three-point curvature scales as **1/Δt²**. Today's cadence is ~18.7 s, and §30.7 already has a 5-second
cadence queued:

| cadence | the same physical curve reads | a cut of 2.0 becomes |
|---|---|---|
| 5 s | **14.0×** today's value | 27.98 |
| 10 s | 3.5× | 6.99 |
| **18.7 s** | 1.00× | 2.00 |
| 30 s | 0.39× | 0.78 |

⇒ ⛔ **a constant in `Q%/min²` is §30.4's `W` mistake in a new costume** — a number derived at one setting and
used at another.

### ⭐⭐⭐ 41.3 · FORM 3 — THE NORMALISED SECOND DIFFERENCE. This is the keeper.

```
D2(i)  =  ( q[i-1] - 2*q[i] + q[i+1] ) / tailSd            dimensionless: Q% over Q%
ADMISSIBLE  iff  D2 < 20
```

| | |
|---|---|
| correct minima, thirteen runs | **0.9 – 6.6** |
| 006's spurious star | **77.5** |
| ⇒ gap | **11.8×** |

⭐ And a sweep of the cut at **20 / 30 / 40 / 50 agrees with the drawdown rule on 13 of 13 runs** — it is a
plateau, not a knife edge.

#### ⭐⭐ Why it is cadence-free where raw curvature is not

For pure noise the second difference has sd **√6 · σ_row**, and `tailSd ≈ σ_row` — so **a noise dip sits at
D2 ≈ 2.4 whatever the cadence**, and a 3σ excursion at ~7. Both numerator and denominator are amplitudes in
`Q%`; nothing is divided by Δt. ⇒ the cut is a **statement about noise**, not about sampling.

⚠ Read what the numbers then say: the correct minima sit at **0.9 – 6.6, i.e. at or below the level noise
alone produces.** A genuine settling basin is so broad that its second difference is invisible. And 006's
star at **77.5 is 32× the noise level — it is not noise at all**, it is a real, fast physical excursion in
the fill. ⭐ The rule is not "reject noise"; it is **"reject anything too sharp to be a settling minimum."**

#### ⭐⭐⭐ AND IT IS LOCAL — which the drawdown rule is not

`D2` needs **one row after the candidate**. `drawdown` and `tailSd` need the whole run.

⇒ ⭐ **`D2` can run live, during acquisition**; it can feed the coach line and, in principle, a gate.
§40.5 said the drawdown rule forces an end-of-run read; **Edwin's curvature idea removes that constraint.**

⚠ `tailSd` is still an end-of-run quantity. ⭐ A live implementation substitutes the **running** residual
scatter of the last 8 rows, which is available from row 9 onward and converges to `tailSd`.

### ⭐⭐ 41.4 · THE RECOMMENDATION — use BOTH, they are complementary

| | `D2 < 20` (Edwin) | `drawdown ≤ 10 × tailSd` (§40) |
|---|---|---|
| what it asks | *is this dip too sharp to be a basin?* | *does the curve ever come back down after it?* |
| gap on the archive | **11.8×** | **14.2×** |
| when it can be evaluated | ⭐ **one row later — LIVE** | ⛔ end of run only |
| cadence-dependent | ⭐ no | ⭐ no |
| agreement on 13 runs | ⭐⭐ **identical** | ⭐⭐ **identical** |

⭐⭐ **Both give 19.782 for 006 and leave the other twelve untouched.** They are independent questions about
the same defect — one about the shape *at* the candidate, one about the history *after* it — so requiring
**both** costs nothing on this archive and covers two different ways to be wrong.

⇒ ⭐ **`D2` runs live and can stop a run from settling on a spike; `drawdown` is the authoritative read at
the end. A disagreement between them is a run worth looking at by hand**, and the record should say so.

⚠ ⛔ **`D2` does NOT rescue the early stop.** 006's star is rejected at t = 244 s, but knowing the star is
bad does not tell you the run may end — the real minimum arrives 3 minutes later. **P1's fixed duration
still stands**; `D2` just makes the run honest while it is running.

### ⛔⛔ 41.5 · D2 ALONE CANNOT REFUSE RUN 003 — AT ANY CUT  *(Edwin: "I would use D2")*

Replaying `D2 < 20` over the whole archive reproduces every answer and repairs 006 — **but it answers 003**,
which the drawdown rule refuses:

| run | before (shipped) | 2.0 deepest min | its `D2` | **after, `D2 < 20`** | drawdown rule |
|---|---|---|---|---|---|
| **Billa 006** | ⛔ 18.989 | 18.989 | **77.5** | ⭐ **19.782** | ⭐ 19.782 |
| **Billa 003** | ⛔ 8.450 | 21.015 | 17.5 | ⚠ **21.015** | ⭐ **NO ANSWER** |

⛔ **And no cut fixes it.** 003 has a *second* local minimum at t = 529.0 s with `D2 = 2.9` — a broad, gentle
wiggle on a curve that is still descending — so tightening the cut merely moves the answer from 21.035 to
21.205:

```
cut  8 / 10 / 12 / 15  ->  003 answers 21.205
cut 20                 ->  003 answers 21.035
correct                ->  no answer (the fill never settled; it was still falling at -0.13 /min)
```

⚠ **C1 does not help either** — 003's two minima both sit at `A_Soret` 0.83–0.94, well under the ceiling, so
dropping the dark-floor rows leaves them untouched.

#### ⭐⭐ Why: the two rules ask different questions, and only one of them is about *settling*

| | asks | 003 |
|---|---|---|
| `D2` | *is this dip too **sharp** to be a basin?* | ⛔ **no — it is a perfectly gentle basin.** It just is not the last one. |
| drawdown | *does the curve ever come **back down** after it?* | ⭐ **yes, by 0.9** ⇒ not a settling minimum |

⇒ ⭐⭐⭐ **`D2` is a shape test; drawdown is a *finality* test.** A run that has not finished clearing
produces gentle, well-shaped, entirely spurious minima all the way down — and only the finality test can see
that. **On this archive the drawdown rule is strictly stronger: it catches everything `D2` catches, plus 003.**

#### ⭐ The recommendation, unchanged in substance but now with a reason

- ⭐⭐ **drawdown is the ANSWER rule.** It is the one that can refuse.
- ⭐ **`D2` is the LIVE rule.** It is the one that can run during acquisition (§41.3) and tell the operator
  *"that dip was not real"* three minutes before the run ends.
- ⚠ **Neither replaces P1.** 003's real problem is that it stopped at 13.9 minutes while still falling at
  0.13 /min; the fixed 20 minutes is what gives such a fill the chance to settle, and the drawdown rule is
  what refuses it honestly if it does not.

---

## ⭐⭐ 42 · WHAT I WOULD ACTUALLY BUILD — the shortlist after §32–§41  *(Edwin asked, 2026-08-20; DESIGN, nothing built)*

> ⭐ **The whole algorithm on one page:** `docs/figures/settling_algorithm_overview.png` — the acquire loop,
> the stop conditions, the read, what the record carries, the lab protocol, and the W0 prerequisite, with the
> seven §42 changes marked in green against what is already built.
> ⭐ And the drawdown rule on its own: `docs/figures/drawdown_explained.png`.

⭐ Six sections of analysis produced a lot of candidates. **Most of them should not be built.** This is the
list that survives, in landing order, with what each one costs and why it is safe.

### ⭐⭐ 42.0 · W0 — THE REPLAY HARNESS. First, and it is the safety net for everything after it.

A test that drives the **real** `ClearingEvaluator.decide()` over the archived `monitorRecord` rows of all
sixteen runs and asserts each recorded answer. The records are already on disk inside the report PDFs
(`workflow.json` → `monitorRecord.rows`), so this needs **no camera, no plugin, no Qt** — §21/M-note already
says `decide()` is pure arithmetic over rows.

⛔ **Without it, W2 and W3 are unverifiable claims.** Every "ten runs bit-identical" in §40 and §41 was
computed *outside* the evaluator by me; W0 is what makes those statements the tree's, not mine.

⚠ Extract the rows into a fixture file at build time — do **not** make the test read PDFs.

### ⭐⭐⭐ 42.1 · W1 — C7: the three band rates in the record and one line on the report

```
006  read at t = 412.9 s -- still clearing: A_Soret -1.06 %/min, A_valley -3.04 %/min, A_Q -1.85 %/min
```

- **All three rates are already computed every row.** This is three numbers into `MonitorRecord` and one
  line into the report.
- ⭐ **Highest value per line in the whole list.** It would have told Edwin not to trust 19.867 *on the
  evening he measured it* (§33.4), with no new physics, no threshold, and no experiment.
- ⛔ Depends on nothing. **Build it first.**

### ⭐⭐ 42.2 · W2 — the drawdown admissibility test in `__read`

```python
drawdown(i)  = max over j>i of ( max(q[i+1..j]) - q[j] )
tailSd       = residual sd of the last 8 decision rows about a line
admissible   = drawdown(i) <= DRAWDOWN_TAIL_MULTIPLE * tailSd     # 10
answer       = vertex around the DEEPEST admissible local minimum
```

- lives in `ClearingEvaluator` beside `__depthOf` — **~30 lines**, one new class constant, one new
  diagnostic field.
- ⭐ **Replay: ten runs bit-identical, 006 repaired 18.989 → 19.782, 003 correctly refused** (§40.4).
- ⭐ threshold gap **14.2×** — derived, not chosen.
- ⛔ **Keep the existing "the minimum is still the newest look, waiting for its far side" guard**, or a
  last-row minimum has drawdown 0 and always wins (§40.5).
- ⚠ It is an end-of-run read. Today the gate decides when the run ends; that is fine — the rule reads over
  whatever rows exist. W7 makes it better, it is not a prerequisite.

### ⭐⭐ 42.3 · W3 — C1: the absorbance ceiling, with its own row state

- a row whose `A_Soret` exceeds `VALUE_CEILING` (1.5, **already in the file**) becomes **`tooDark`**.
- ⛔⛔ **`tooDark` must NOT be the same as `values = {}`** or run 003 aborts at t ≈ 40 s as
  `MEASUREMENT_BROKEN` (§32.4a). Sub-floor = *abort, nothing in the cuvette*; over-ceiling = *wait, it is
  still clearing*.
- the coach says *"too dark to read — still clearing"* instead of the current silence.
- ⭐ Replay: **nine of twelve runs untouched**, Lugitsch 006 and Billa 001 lose 5 and 2 opening rows with no
  change of answer, Billa 003 loses its first 21 (§32.4).
- ⚠ Touches `MonitorEngine` (the row state) as well as the plugin (the test) — the only item here that
  crosses the SDK boundary.

### ⭐ 42.4 · W4 — record what the run knew about itself

Three recordings, no gating, no thresholds:

| field | why |
|---|---|
| `clearingObserved` — fractional fall of `A_valley` from the first admissible look to the read | 002: **1.6 %**; 003: 97.8 %. The pair *(level, fall)* is diagnostic even though neither alone is (§32.7/C3) |
| `A_valley` **at the promoted row** | the answer's clearing state; needed by every cross-run comparison (§39.1's matched-turbidity method) |
| the **reference band means** (Soret / valley / Q) | P7. The reference wanders ±3 % run to run (§38.6); today that wander is invisible in the record |

⭐ All three are numbers already in memory at promotion time.

### ⛔ 42.5 · W5 — ⚠ **WITHDRAWN by Edwin, 2026-08-20 (§43/RD10): do not persist it.** Kept for the record.

§15.1 stores the answer's spectrum, which is right for the verdict and wrong for shape comparison: the
answer sits at the `Q%` minimum, i.e. **a different turbidity for every fill** — sd 0.0398 across the five
good Billa fills against the last row's 0.0182, **2.2× tighter** (§37.4, figure `w5_two_spectra.png`).

⭐ One extra array per run, and it is what unblocks the history tracker's shape half later.

### ⛔ 42.6 · W6 — ⚠ **KILLED by §43/RD5: with a running scale `D2` never fires.** Kept for the record.

```
D2(i) = ( q[i-1] - 2*q[i] + q[i+1] ) / runningTailSd        reject the candidate if D2 >= 20
```

- ⭐ **Local — one row after the candidate**, so unlike W2 it can run *during* acquisition (§41.3).
- it does not change the answer (W2 does that); it lets the coach say *"that dip was not real"* three
  minutes before the run ends, instead of the operator finding out from the report.
- ⛔ **Not a substitute for W2**: `D2` cannot refuse run 003 at any cut (§41.5). Shape test vs finality test.
- ⚠ Needs a *running* tail scatter rather than the final one; available from row 9.

### ⚠ 42.7 · W7 — P1: fixed run duration, as a SETTING with default 20 min

- ⭐ Two independent arguments: it makes dose equal across fills, which deletes §2.4's varying-clearing-time
  term from σ_fill (§34.6); and it guarantees the browning limb has time to **confirm** the minimum — 001
  outlasted its own minimum by **one row** (§36.5).
- ⚠ **The number 20 is provisional** until §33.8's T0 (one fill driven to completion). ⭐ Which is why it is
  a setting: shipping it as a setting costs nothing and does not pretend the constant is derived.
- ⛔ Do not remove the gate. Let it run to the clock and record when the gate *would* have fired — that is
  free evidence for whether the clock or the gate should win later.

### ⛔ 42.8 · WHAT I WOULD **NOT** BUILD, AND WHY

| | verdict |
|---|---|
| **C2** — the `A_valley ≤ 2 × min` hunt window (§32.7) | ⭐ **Drop it.** Its only case in the whole archive was run 003, and W2 + W3 both catch 003 independently. A rule with no remaining case is a rule that can only misfire. |
| **C4** — the κ turbidity correction (§32.6) | ⛔ **Withdrawn.** Per-run slopes disagree in sign; extrapolating to zero turbidity triples the scatter (sd 1.346 vs 0.467, §39.5). |
| **C5** — the relative-rate gate on `A_Soret` (§33.7) | ⚠ **Defer.** The finding behind it stands — the gate watches one band's absolute rate — but `theta_rel` is not derivable from the archive, and 004/005/007 show the current gate producing correct answers. Revisit after T1. |
| **C3 as a verdict** — "this fill never cleared" | ⚠ **Record it (W4), do not gate on it.** The level threshold is not derivable: 002's 0.204 is only 1.35× the next-highest terminal `A_valley` (§32.5). |
| **C6** — residual turbidity against the stock's clear value | ⚠ Needs a per-stock "clear", which is the history tracker's job. Later. |
| **the history tracker itself** | ⚠ Buildable (§37.7) but wait: the **scalar** half is the valuable one (40× more sensitive than the shape half, §37.9), and it wants T1's σ_fill to set its band. The shape half wants W5 first. |
| **P8** — matched-`A_valley` comparison | ⭐ It is an **analysis method** (§39.1), not a product feature yet. Keep it in the diagnostics scripts until two runs need comparing inside the app. |
| **P6** — record the pour position | ⛔ **Withdrawn** (§39.2). Replaced by **P6′**, which is a lab rule and not code: *aliquots stay in the dark*. |

### ⭐ 42.9 · THE ORDER, AND WHY IT IS THIS ORDER

```
W0  replay harness            <- the safety net; nothing below is verifiable without it
W1  band rates in the record  <- zero risk, zero dependencies, highest value per line
W4  clearingObserved + A_valley at the read + reference band means
W2  drawdown admissibility    <- the answer changes here; W0 is what makes that safe
W3  ceiling + tooDark         <- crosses into the SDK; do it after the read is settled
W5  last row's spectrum
W6  D2 in the coach
W7  fixed duration as a setting
```

⭐ **W0 + W1 + W4 change no answer at all** — they are pure recording and can land in one commit with the
tree green. **W2 is the only step that moves a number**, and it moves exactly one (18.989 → 19.782).

⚠ And the honest caveat on all of it: **the clean set is four fills.** Everything above is derived from an
archive of sixteen monitored runs, six of them from one evening. §35's T1 is still owed, and it is what
turns these constants from *"derived with a gap"* into *"measured"*.

---

## ⭐⭐ 43 · RUBBER-DUCK PASS ON §42 — walked against the AS-IS code  *(Edwin asked for it, 2026-08-20)*

⭐ Ten findings. **One kills an item outright, one is a prerequisite nobody costed, and one is Edwin's own
call.** The list of seven becomes a list of five plus a new seam.

### ⛔⛔ RD1 — THERE IS NO END-OF-RUN HOOK, AND W2 AND W7 BOTH NEED ONE

`MonitorEngine.decide()` is reached from exactly one place:

```python
def offer(...):
    ...
    if row.isDecisionRow and not self.__finished:
        self.__applyDecision(row)          # <- the ONLY caller of evaluator.decide()
    self.__enforceCaps()
```

and `__finish()` — reached from `__enforceCaps`, `cancel()`, `stall()` and `decision.stop` — **never calls
the evaluator again.** ⇒ **the evaluator is never asked *"the run is over, what is your answer?"***

⛔ §40.5 established that the drawdown read is **end-of-run** (`tailSd` and `drawdown` both need the rows
*after* a candidate). ⛔ §34/W7's fixed duration ends a run on the clock, with nothing promoted.
**Neither can be built on today's seam.**

#### ⭐ The fix: a `finalize(rows)` seam — and it is small

```python
def __finish(self, outcome):
    if self.__finished: return
    final = getattr(self.evaluator, "finalize", None)
    if final is not None and self.__error is None:
        try:    self.__applyFinal(final(list(self.rows)))
        except Exception: self.__error = traceback.format_exc()
    self.outcome = ...
    self.__finished = True
```

⚠ **`__pruneSpectra` must have kept the winner.** Retention is `maxSeconds` (§27.25), and the fixed duration
is ≤ `maxSeconds`, so every decision row still holds its spectrum at finalize time. ⛔ **W7 must therefore
NOT implement itself by lowering `maxSeconds`** — that would shrink retention along with the run.

### ⛔ RD2 — `clearingSeconds` SILENTLY BECOMES "the run length"

`__applyDecision` sets `self.__clearingSeconds = row.t` **at the moment of promotion**. Under a finalize-time
read the promoting row is always the last one ⇒ **`clearingSeconds` degenerates to the run duration** and
§2.4's "log the clearing time, it is a σ_fill component" quietly stops being logged.

⭐ Fix: the evaluator already knows when the gate fired (`__gateIndex`). Carry `gateSeconds` in
`diagnostics`, and let the engine keep `clearingSeconds` for whatever still sets it.

### ⭐ RD3 — `tooDark` needs NO SDK change, and here is the exact shape

⛔ §32.4a says `tooDark` must not be `values = {}`. The minimal implementation keeps the SDK untouched:

- the plugin's `monitorMetrics()` returns `{}` below the floor (as today) and **`{"tooDark": 1.0}`** above the
  ceiling;
- `ClearingEvaluator.decide()` drops `tooDark` rows from `decisions` **before anything else**;
- the `MEASUREMENT_BROKEN` test counts only rows whose `values` are genuinely **empty**.

⭐ Three free consequences: `MonitorRow.values` stays opaque to the engine; `toDict()` carries the flag into
the record, so the report can show *which* rows were unreadable; and `MONITOR_COLUMNS` is declared
explicitly, so no plot or table changes.
⚠ One waste to fix: `__evaluateIfDue` attaches a spectrum to **every** decision row — a `tooDark` row will
hold a spectrum that can never be read. Prune it at creation.

### ⚠ RD4 — W6's coach line collides with §17/U1

§17/U1 is categorical: *"DO NOT SHOW A PROVISIONAL `Q%`. AT ALL."* A live *"that dip was not real"* announces
that there **was** a dip and invites the operator to ask how deep. ⇒ the wording may say a spike was
rejected; it may **never** name a value, a depth or a direction.

### ⛔⛔ RD5 — W6 CANNOT RUN LIVE. MEASURED, AND IT KILLS THE ITEM.

§41.3 claimed `D2` is local: *"it needs one row after the candidate"*. **The numerator does. The denominator
does not** — `tailSd` is the quiet tail of a finished run. Replacing it with a **running** last-8-rows
scatter, which is all a live check can have:

| run 006, local minimum | running `tailSd` | `D2` live | final `D2` |
|---|---|---|---|
| t = 169.6 s | 0.1250 | 5.7 | — |
| **t = 225.5 s — the spurious star** | **0.2481** | ⛔ **2.6** | **77.5** |
| t = 412.9 s — the real minimum | 0.1544 | 0.3 | 4.8 |

⛔⛔ **`D2` never fires anywhere, on any of the four good runs, with a running scale.** The reason is
structural: during the noisy stretch the running scatter is *itself* inflated by that same noise (0.248
against the final 0.0084), so the dip is small **relative to its own neighbourhood**. The 77.5 exists only
because the final tail is quiet.

⇒ ⭐ **DROP W6.** At end-of-run `D2` and drawdown agree on all thirteen runs (§41.4), so `D2` adds nothing
there; and the one property that justified it — running live — is not real. ⚠ §41.3 and §41.4's
"⭐ LOCAL / can run live" claims are **withdrawn**; §41.5's shape-vs-finality analysis stands.

### ⚠ RD6 — THE EXISTING TESTS ASSERT PROMOTION FROM `decide()`, AND §19/I5 SAYS DO NOT REWRITE THEM

`test_clearing_evaluator.py` inspects `decision.promote` / `decision.promoteRow` in at least five tests
(`..._lands_on_the_measured_Q_MINIMUM_not_on_the_gate_row`, `..._an_ALREADY_CLEAR_fill_settles_immediately`,
`..._a_fill_that_never_clears_never_promotes`, `..._the_read_WAITS_when_the_minimum_is_still_the_newest_look`,
`..._DIAGNOSTIC_mode_reads_the_answer_but_does_NOT_stop`). Moving the read wholesale into `finalize()`
breaks all of them.

⭐ **Keep `decide()` exactly as it is.** `finalize()` calls the SAME `__read()` over the complete row list
and may **revise** the latched answer once.

⛔⛔ **That is an amendment to §14.6 and must be written as one.** §14.6's latch exists so that *observation
during a run cannot move the answer*; **one end-of-run revision is a different act**, and the record must
say which read produced the value — a `readPhase: "gate" | "final"` field — or two runs stop being
comparable.

### ⚠ RD7 — THE OUTCOME SET HAS NO "the clock ran out as planned"

Today a cap with nothing promoted gives `NEVER_SETTLED` — *"a cap was hit with the gate never firing, NO
value"*. Under W7 the clock running out is the **normal** ending. ⇒ `MonitorPolicy` needs an additive
`plannedSeconds` (distinct from `maxSeconds`, which stays the un-removable guarantee), and finalize decides
the outcome. ⭐ Additive fields orphan no saved record (§30.12's rule).

### ⭐ RD8 — W1 AND W4 ARE FREE, INCLUDING THE ONE THAT LOOKED EXPENSIVE

All three band rates and `clearingObserved` fall out of `__readDiagnostics`, which already exists and already
rides into the record inside `answer["diagnostics"]` — **no record key, no result field, no migration**
(§30/R2.1). ⭐ And the **reference band means** are reachable too: the evaluator holds `self.__reference`,
so it can compute them once at read time.

### ⚠ RD9 — W0's FIXTURE MUST PIN *RECOMPUTED* ANSWERS, NOT THE PRINTED ONES

Seven of the sixteen archived runs are `clearing-1.0` records (§36.9). Their printed answers were produced
by the rule §29 replaced. ⇒ the fixture stores **the rows** plus **the `clearing-2.0` answer recomputed once
and pinned**, and the harness asserts against that. ⛔ Asserting against the printed value would encode the
old rule as the expectation.

### ⭐ RD10 — W5 IS WITHDRAWN  *(Edwin: "I do not want this to be persisted")*

⭐ **Dropped.** `MonitorRow.spectrum` is transient and absent from `toDict()`, so W5 would have meant a new
`MonitorResult` field, a new record key and a persistence change — for a metric that is already 40× less
sensitive than the scalar tracker (§37.9).

⚠ What it costs, stated honestly: the history tracker's shape distance keeps a within-oil floor inflated by
the clearing-state spread (sd 0.0398 at the answer against 0.0182 at the last row, §37.4). **It costs
sensitivity, not correctness** — §37.7's separation is 1.46× worst case with no overlap across 45 pairs.

⭐ **And W4 covers the honest half for free:** `A_valley` at the promoted row is persisted, so the tracker can
*see* when two spectra were taken at very different clearing states and **flag the comparison** rather than
silently making it.

---

## ⭐⭐ 44 · IMPLEMENTATION PHASES — after the rubber duck  *(2026-08-20; DESIGN, nothing built)*

⭐ Five phases. **Each one leaves the tree green**, and the order is chosen so the phase that changes an
answer lands *after* the phase that can prove it did not change any other.

### ⭐ PHASE A — the harness and the recording  *(no answer changes at all)*

| | what | where |
|---|---|---|
| **A1** | **W0 · replay fixture** — extract the `monitorRecord` rows of all sixteen archived runs into `tests/data/monitor_replay.json`, with the `clearing-2.0` answer recomputed once and pinned (RD9). | new fixture |
| **A2** | **W0 · replay test** — drive the real `ClearingEvaluator.decide()` over every fixture run and assert the pinned answer. ⭐ From here on, "ten runs bit-identical" is the tree's claim, not a spreadsheet's. | `tests/` |
| **A3** | **W1 · the three band rates** into `__readDiagnostics`, and one line on the report. | plugin |
| **A4** | **W4 · `clearingObserved`, `A_valley` at the promoted row, the reference band means** — same dict, no record key, no migration (RD8). | plugin |

⭐ **A1–A4 change no number.** A2 must pass before and after A3/A4, which is the point.

### ⭐⭐ PHASE B — the seam  *(no answer changes; the mechanism to change one)*

| | what | where |
|---|---|---|
| **B1** | **`finalize(rows)` on the evaluator contract**, called once from `MonitorEngine.__finish()` before the outcome is set (RD1). Absent on an evaluator ⇒ nothing happens, so the burst plugin (§10.6) is untouched. | SDK |
| **B2** | **the latch amendment** — one end-of-run revision is permitted; write it into §14.6 as an amendment, and add **`readPhase: "gate" \| "final"`** to the answer (RD6). | SDK + spec |
| **B3** | **`gateSeconds` into diagnostics**, so `clearingSeconds` does not degenerate into the run length (RD2). | plugin |
| **B4** | **`ClearingEvaluator.finalize()` = today's `__read()` over the whole row list.** ⭐ At this point it must reproduce the gate-time answer on all sixteen fixture runs — a pure refactor, proven by A2. | plugin |

⚠ B4 is the checkpoint: **if finalize and the gate disagree anywhere before C1 lands, the seam is wrong, not
the rule.**

### ⭐⭐ PHASE C — the read  *(the only phase that moves a number)*

| | what |
|---|---|
| **C1** | **W2 · drawdown admissibility** inside `__read` — `drawdown(i) ≤ DRAWDOWN_TAIL_MULTIPLE × tailSd`, `DRAWDOWN_TAIL_MULTIPLE = 10`, answer = the vertex around the deepest admissible minimum. ⛔ Keep the "waiting for its far side" guard. |
| **C2** | update the A1 fixture: **exactly two rows change** — Billa 006 `18.989 → 19.782`, Billa 003 `8.450 → no answer`. Everything else byte-identical. |
| **C3** | the record carries `drawdown`, `tailSd` and the rejected candidates, so a refusal can be argued with rather than believed. |

### ⭐ PHASE D — the input guard

| | what |
|---|---|
| **D1** | **W3 · the ceiling** — `monitorMetrics()` returns `{"tooDark": 1.0}` above `VALUE_CEILING`; `decide()` filters those rows first; the `MEASUREMENT_BROKEN` count uses genuinely-empty values only (RD3). |
| **D2** | do not attach a spectrum to a `tooDark` row (RD3). |
| **D3** | coach: *"too dark to read — still clearing"*; the ⛔ INDETERMINATE bar stays (§17/U3 has nothing to predict from). |
| **D4** | fixture: **nine of twelve runs untouched**, 006L and Billa 001 lose opening rows with no change of answer, Billa 003 loses its first 21. |

### ⚠ PHASE E — the clock  *(ship as a setting; the number is provisional)*

| | what |
|---|---|
| **E1** | `MonitorPolicy.plannedSeconds`, additive, distinct from `maxSeconds` (RD7). ⛔ Never implement W7 by lowering `maxSeconds` — that shrinks spectrum retention with it (RD1). |
| **E2** | a `PLANNED_END` outcome, or finalize choosing among the existing ones; `NEVER_SETTLED` keeps its meaning of *"the guarantee cap fired"*. |
| **E3** | the gate keeps running underneath and the record says when it **would** have fired — free evidence for the clock-versus-gate question. |
| **E4** | the Frames/duration control in the bench, default 20 min. |

### ⛔ 44.1 · WHAT IS NOT IN ANY PHASE

| | why |
|---|---|
| **W5** — persist the last row's spectrum | ⭐ **Edwin's call** (RD10). Costs shape-tracker sensitivity, not correctness. |
| **W6** — `D2` as a live check | ⛔ **Killed by RD5** — measured: with a running scale it never fires, including on the star it was written for. At end-of-run it duplicates C1. |
| C2 hunt window · C4 κ · C5 relative gate · C3-as-verdict · C6 · P8 · the history tracker | §42.8, unchanged. |

### ⭐ 44.2 · THE SHAPE OF THE WHOLE THING

```
A  harness + recording      no answer moves      <- prove the baseline
B  the finalize seam        no answer moves      <- prove the mechanism
C  the drawdown read        TWO answers move     <- the actual change
D  the ceiling              no answer moves      <- one run gains a refusal it already had from C
E  the clock                no answer moves      <- a setting, and the number is provisional
```

⭐⭐ **Only phase C moves a number, and it moves two.** ⚠ Everything above rests on four clean fills from
one evening; §35's T1 is what turns the constants from *derived-with-a-gap* into *measured*, and it does not
block any of A–E.

---

## ⭐⭐ 45 · SECOND RUBBER-DUCK PASS — the MECHANICS of writing it  *(Edwin, 2026-08-20)*

⭐ §43 asked *"is the design right?"*. This asks *"what will bite the person typing it?"* — the §21 question.
Nine findings; **two are check-before-you-write-a-line, one is a silent failure mode.**

### ⛔⛔ M1 — IS THE BENCH RUNNING THE FILE, OR A SEALED DB ROW? CHECK THIS FIRST.

`PluginRegistry` line 83, verbatim: *"a published sealed row **OVERRIDES** the built-in, while the seed's
bare rows and offline both fall back."*

⇒ **if a sealed `dev.DevSpectralPlugin` row exists in the server DB for the version the bench binds to,
every edit to `spectracs-plugins/.../DevSpectralPlugin.py` changes nothing at the rig.** ⚠ This exact class
of confusion is already in the record — *"bit me seeding DB plugins that never appeared in the bench"* —
and it costs an evening if it is discovered after the change instead of before.

⭐ **The check is one query, and it belongs in A0**, before anything else. Note the server DB is CWD-dependent
(`runServer.sh` → `~/.spectracsPy-server/*.db`).

### ⛔⛔ M2 — FIVE REPOS, NO VERSION PIN, AND A SKEW FAILS **SILENTLY** — CHANGING THE ANSWER

`spectracsPy` · `spectracsPy-core` · `spectracs-plugins` · `spectracsPy-model` · `spectracsPy-base` are five
separate git repos joined only by `PYTHONPATH`. The finalize seam splits across two of them:

```
spectracsPy-core     MonitorEngine.__finish()  ->  probes evaluator.finalize
spectracs-plugins    ClearingEvaluator.finalize()
```

⛔ **An old core with a new plugin is not an error — the probe simply finds nothing, finalize is never
called, and the run silently reverts to the gate-time answer.** No exception, no log line, and on 006 the
number goes back to 18.989.

⭐ **`readPhase` (§43/RD6) is the detector, and that promotes it from nice-to-have to required**: a record
that says `"gate"` when the operator expected `"final"` names the skew immediately. ⚠ Land **core first**,
plugins second, and assert `readPhase == "final"` in the replay test.

### ⭐ M3 — THE EXISTING TEST DOUBLES ARE PLAIN CLASSES, SO THE `getattr` PROBE IS SAFE

`test_monitor_engine.py` uses `FakeEvaluator`, `PromoteAlways`, `NeverSettles`, `RaisesLate`,
`BurstEvaluator`; `test_the_winner_keeps_its_spectrum.py` uses `PromotesAnOldRow`. **None is a `MagicMock`.**
⇒ `getattr(evaluator, "finalize", None)` returns `None` for all of them and B1 breaks no test.

⛔ **The rule this establishes must be written down**: a `MagicMock` evaluator would return a truthy callable
for *any* attribute, so the probe would call a mock and hand its return value to `__applyFinal`. **Future
doubles stay plain classes.**

⭐ And `BurstEvaluator` (the SDK's degenerate monitor, §10.6) must **not** grow a `finalize` — a plain burst's
answer is its last row, decided at `decide()` time, and giving it an end-of-run read would change §10.6's
shape for no reason.

### ⛔ M4 — `tailSd` OVER "THE LAST 8 ROWS" HAS NO RULE FOR A SHORT RUN. **OPEN.**

Run 002 has **six** decision rows. `tailSd` needs at least 4 for a residual-about-a-line with `ddof=2` to
mean anything, and 8 is what every number in §40 was computed with.

⚠ 002 happens not to reach the drawdown path (a monotone rise has no interior minimum), so the archive does
not force the question — **which is exactly why it will be met first on the rig.** ⇒ **decide it now**:

| rows available | proposal |
|---|---|
| ≥ 8 | as specified |
| 4 – 7 | use what there is, and **record `tailRows`** so the number can be discounted later |
| < 4 | ⛔ no drawdown test is possible ⇒ **fall back to today's read** and say so in the record |

### ⛔ M5 — DOES `finalize()` RUN ON A CANCEL, A STALL, A FAILURE? **THREE DECISIONS, NOT ONE.**

`__finish()` is reached from five paths and they do not mean the same thing:

| path | run finalize? | why |
|---|---|---|
| `decision.stop` (settled / degrading) | ⭐ **yes** | the normal ending |
| caps / planned duration | ⭐ **yes** | this is the ending W7 exists for |
| `FAILED` | ⛔ **no** | the evaluator just raised; calling it again invites a second traceback over the first |
| `CANCELLED` | ⚠ **no** — §12.1: *"a cancelled capture is not a capture"* | the trajectory is kept and marked, not read |
| `STALLED` | ⚠ **yes, but the outcome stays `STALLED`** | frames stopped; the rows that exist are real, and refusing to read them throws away a run the operator cannot repeat cheaply |

⭐ Encode it as an explicit set in `__finish()`, not as an `if` nobody can find later.

### ⚠ M6 — DO NOT REUSE `VALUE_CEILING` FOR THE MONITOR

`VALUE_CEILING = 1.5` exists to **drop saturated λ inside a band computation**. The monitor's ceiling asks a
different question — *"is this whole row a measurement?"* — and the two will want to move apart the first
time either is re-derived. ⭐ **A separate `MONITOR_SORET_CEILING`, its own comment, the same 1.5 today.**
⛔ Sharing the constant is exactly the trap this file's own opening comment describes about the two retired
gauges.

### ⚠ M7 — WHEN finalize REVISES, THE GATE-TIME ANSWER MUST SURVIVE

Otherwise the only evidence that a revision happened is a version string. ⭐ Keep it in `diagnostics`:

```
readPhase: "final"        gateAnswer: 18.989        gateSeconds: 658.5        answer: 19.782
```

⚠ It costs three JSON keys and rides inside `answer`, which `toRecord()` serialises wholesale — **no record
key, no migration** (§43/RD8).

### ⭐ M8 — THE WRITE ORDER THAT KEEPS EVERY COMMIT GREEN

```
1  spectracsPy        A1 fixture + A2 replay test        green (asserts today's behaviour)
2  spectracs-plugins  A3 band rates + A4 recording       green (A2 still passes — no answer moved)
3  spectracsPy-core   B1 finalize seam (probe only)      green (no evaluator defines finalize yet)
4  spectracs-plugins  B3 gateSeconds + B4 finalize=read  green  <- THE CHECKPOINT: A2 must still pass
5  spectracsPy        B2 readPhase assertion in A2       green
6  spectracs-plugins  C1 drawdown                        RED until 7
7  spectracsPy        C2 fixture: exactly two rows move  green
8  spectracs-plugins  D1-D3 ceiling + tooDark            green
9  spectracsPy        D4 fixture check                   green
10 core + plugins + app   E1-E4 the clock                green
```

⚠ **Step 6 is the only red one, and it is red on purpose** — the fixture is the thing being changed, so it
must be changed in a separate commit that says which two numbers moved and why.

### ⭐ M9 — SMALL THINGS, EACH CHEAP NOW

- ⭐ **No `SDK_VERSION` bump** (§19/I2 stands): an *optional* seam probed by `getattr` is backwards
  compatible in the direction that matters — an old plugin on a new core is fine.
- ⭐ **The android tree's `DevSpectralPlugin.py` is a 269-line spike stub**, not a copy of the 2105-line real
  one. **No sync burden** — but say so, or someone will try to keep them in step.
- ⚠ `toRecord()` serialises `decisionRows()` only. A `tooDark` row **is** a decision row, so `{"tooDark": 1.0}`
  reaches the record for free and the report can show which rows were unreadable.
- ⚠ `CapturePanel.py:902` is the single write point (`workflow.setMonitorRecord(result.toRecord())`) — **no
  host change is needed for any of A–D.**
- ⚠ `MonitorPolicy` raises on a non-positive `maxSeconds`. `plannedSeconds` must validate the same way **and
  additionally** that `plannedSeconds ≤ maxSeconds`, or retention (§43/RD1) silently outlives the run.

### ⛔ 45.1 · SO: IS EVERYTHING AT HAND?

| | |
|---|---|
| ⭐ **the rules** | yes — every threshold is derived with a stated gap and replay-verified on sixteen runs |
| ⭐ **the data** | yes — all sixteen records are on disk inside the report PDFs |
| ⭐ **the seams** | yes, after B1; the write point, the record path and the report path all exist |
| ⛔ **M1** | **unknown until checked** — sealed DB row versus the file. One query, and it gates everything. |
| ⛔ **M4** | **undecided** — `tailSd` on a short run. Proposal above; needs a yes. |
| ⛔ **M5** | **undecided** — finalize on cancel/stall/failure. Proposal above; needs a yes. |
| ⚠ **the 20 minutes** | provisional until §33.8's T0. ⭐ Does not block A–D; E ships it as a setting. |
| ⚠ **the constants** | derived from **four clean fills of one oil on one evening**. §35's T1 is what makes them measured. |

---

## ⭐⭐ 46 · IMPLEMENTATION PHASES — the table  *(supersedes §44's prose; DESIGN, nothing built)*

```
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| STEP | WHAT                                   | REPO                | SIZE  | ANSWERS  | GREEN AFTER?    |
+======+========================================+=====================+=======+==========+=================+
|                       PHASE 0  ·  BEFORE A LINE IS WRITTEN                                              |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| A0.1 | Is a SEALED dev.DevSpectralPlugin row  | (server DB query)   |  --   |   none   | n/a  ** M1 **   |
|      | in the DB? If yes the file is IGNORED. |                     |       |          |                 |
| A0.2 | DECIDE M4: tailSd on a run with < 8    | (spec)              |  --   |   none   | n/a             |
|      | decision rows                          |                     |       |          |                 |
| A0.3 | DECIDE M5: finalize on cancel / stall  | (spec)              |  --   |   none   | n/a             |
|      | / failure                              |                     |       |          |                 |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       PHASE A  ·  HARNESS AND RECORDING          no answer moves                        |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| A1   | replay FIXTURE: rows of all 16 archived| spectracsPy/tests   |  ~M   |   none   | yes             |
|      | runs + the RECOMPUTED 2.0 answer (RD9) |                     |       |          |                 |
| A2   | replay TEST: drive the real decide()   | spectracsPy/tests   |  ~S   |   none   | yes             |
|      | over every run, assert the answer      |                     |       |          |                 |
| A3   | W1: three band rates -> diagnostics    | spectracs-plugins   |  ~S   |   none   | yes  (A2 holds) |
|      | + one line on the report               |                     |       |          |                 |
| A4   | W4: clearingObserved, A_valley at the  | spectracs-plugins   |  ~S   |   none   | yes  (A2 holds) |
|      | read, reference band means             |                     |       |          |                 |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       PHASE B  ·  THE SEAM                       no answer moves                        |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| B1   | finalize(rows) probed from __finish(); | spectracsPy-core    |  ~S   |   none   | yes  (no        |
|      | M5's path set; NOT on BurstEvaluator   |                     |       |          |  evaluator has  |
|      |                                        |                     |       |          |  finalize yet)  |
| B2   | readPhase "gate"|"final" on the answer | core + spec         |  ~XS  |   none   | yes             |
|      | + the §14.6 LATCH AMENDMENT written    |                     |       |          |                 |
| B3   | gateSeconds -> diagnostics, so         | spectracs-plugins   |  ~XS  |   none   | yes             |
|      | clearingSeconds does not degenerate    |                     |       |          |                 |
| B4   | ClearingEvaluator.finalize() = today's | spectracs-plugins   |  ~S   |   none   | yes  <== THE    |
|      | __read() over the WHOLE row list       |                     |       |          |  CHECKPOINT     |
| B5   | A2 also asserts readPhase == "final"   | spectracsPy/tests   |  ~XS  |   none   | yes  ** M2 **   |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       PHASE C  ·  THE READ                       TWO answers move                       |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| C1   | W2: drawdown(i) <= 10 x tailSd;        | spectracs-plugins   |  ~M   |  006 and | ** RED **       |
|      | answer = vertex at the DEEPEST         |                     |       |  003     |  until C2       |
|      | admissible minimum. Keep the far-side  |                     |       |          |                 |
|      | guard.                                 |                     |       |          |                 |
| C2   | fixture update: EXACTLY two rows move  | spectracsPy/tests   |  ~XS  |   --     | yes             |
|      | 006 18.989 -> 19.782 ; 003 -> refused  |                     |       |          |                 |
| C3   | record drawdown, tailSd, tailRows and  | spectracs-plugins   |  ~XS  |   none   | yes             |
|      | the REJECTED candidates                |                     |       |          |                 |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       PHASE D  ·  THE INPUT GUARD                no answer moves                        |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| D1   | MONITOR_SORET_CEILING (own constant,   | spectracs-plugins   |  ~S   |   none   | yes             |
|      | M6) -> {"tooDark": 1.0}; decide()      |                     |       |          |                 |
|      | filters first; BROKEN counts empty only|                     |       |          |                 |
| D2   | no spectrum attached to a tooDark row  | spectracs-plugins   |  ~XS  |   none   | yes             |
| D3   | coach "too dark to read"; the          | spectracs-plugins   |  ~XS  |   none   | yes             |
|      | INDETERMINATE bar stays                |                     |       |          |                 |
| D4   | fixture: 9/12 untouched; 006L and      | spectracsPy/tests   |  ~XS  |   none   | yes             |
|      | Billa 001 lose opening rows; 003 -21   |                     |       |          |                 |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       PHASE E  ·  THE CLOCK                      no answer moves                        |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| E1   | MonitorPolicy.plannedSeconds, additive,| spectracsPy-core    |  ~XS  |   none   | yes             |
|      | validated <= maxSeconds  (M9)          |                     |       |          |                 |
| E2   | a planned ending distinct from         | core + plugins      |  ~S   |   none   | yes             |
|      | NEVER_SETTLED (RD7)                    |                     |       |          |                 |
| E3   | the gate runs on underneath; record    | spectracs-plugins   |  ~XS  |   none   | yes             |
|      | when it WOULD have fired               |                     |       |          |                 |
| E4   | the duration control, default 20 min   | spectracsPy         |  ~S   |   none   | yes             |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
|                       NOT IN ANY PHASE                                                                  |
+------+----------------------------------------+---------------------+-------+----------+-----------------+
| W5   | persist the last row's spectrum        |  --  Edwin's call, §43/RD10                          |
| W6   | D2 as a live check                     |  --  killed by §43/RD5 (never fires on a running scale)|
| C2*  | the A_valley hunt window               |  --  §42.8: no case left, and a rule with no case      |
|      |                                        |      can only misfire                                  |
| C4   | the kappa correction                   |  --  §39.5: extrapolation triples the scatter          |
| C5   | the relative-rate gate                 |  --  theta_rel not derivable; revisit after T1         |
| C6 / P8 / the history tracker              |  --  §42.8, unchanged                                  |
+------+----------------------------------------+---------------------+-------+----------+-----------------+

  SIZE:  XS < 20 lines   S ~ 20-60   M ~ 60-150      ANSWERS: which archived answers change
  LANDING ORDER ACROSS REPOS (M2 — a skew fails SILENTLY):  core  ->  plugins  ->  app tests
```

⭐⭐ **Read the ANSWERS column downward: every phase says "none" except C, which says "006 and 003".** That
is the whole safety argument — and A2, written first, is what turns it from a claim into a test.

---

## ⭐⭐ 47 · THE OPEN-QUESTIONS REGISTER — everything §32–§46 left undecided  *(2026-08-20)*

⭐ Six sections of analysis closed a lot. **What is left, in one place**, sorted by what it blocks.
⛔ Nothing here is rhetorical: each one has a proposal or a named experiment.

### ⛔⛔ A · BLOCKS THE IMPLEMENTATION — six answers, all at the desk

| # | question | proposal | who |
|---|---|---|---|
| **A1** | ⛔ **Is a SEALED `dev.DevSpectralPlugin` row in the server DB?** If yes, editing the plugin file changes nothing at the rig (§45/M1). | a check, not a decision — one query against `~/.spectracsPy-server/*.db` | me, first thing |
| **A2** | ✅ **CLOSED 2026-08-20 — Edwin accepted.** `tailSd` when a run has fewer than 8 decision rows (002 has 6) — §45/M4 | ≥8 as specified · 4–7 use what there is and **record `tailRows`** · <4 **fall back to today's read** and say so in the record | ✅ agreed |
| **A3** | ⛔ **Does `finalize()` run on cancel / stall / failure?** — §45/M5. ⭐ **Lean and two refinements in §48.1.** | stop ✅ · caps & planned ✅ · `FAILED` ⛔ · `CANCELLED` ⛔ (§12.1) · `STALLED` ✅, outcome unchanged, answer **recorded but not reported** | Edwin ✔/✘ |
| **A4** | ⛔⛔ **May finalize REVISE a latched answer?** §14.6 says the answer is fixed when read and observation cannot change it (§43/RD6). ⭐ **Lean in §48.2.** | yes, exactly once, with `readPhase` + `gateAnswer` — ⭐ **plus `MonitorEngine.SUPPORTS_FINALIZE` so a repo skew fails loudly at run start**, which buys the alternative's only real advantage | **Edwin — the one real design call left** |
| **A5** | ✅ **DISSOLVED 2026-08-20 — no new outcome is needed.** See §47.2. | ⭐ the outcome comes from finalize as it would anyway (`SETTLED_*` if it found an answer, `NEVER_SETTLED` if it did not); add a **`plannedEnd` boolean beside the existing `capsHit`** so the record still distinguishes "ran its 20 minutes" from "hit the 25-minute guarantee" | ✅ resolved |
| **A6** | ⚠ **Where does W1's band-rate line go** — the PDF report, the bench, or both? | both; it is one `MetricFieldView` with `shownInReport` | me, default |

### ⚠ B · BLOCKS SHIPPING, NOT BUILDING — the rig owes three sessions

| # | question | the session | what it unblocks |
|---|---|---|---|
| **B1** | ⭐⭐ **Is 20 minutes enough — and does a fill ever actually settle?** No run in the archive has ever been watched until it stopped changing. | §33.8 **T0**: one Billa fill, 001's recipe, **60 min**, DIAGNOSTIC, no promotion — **plus a second jar with the lamp SHUTTERED between looks** | E4's default; and it can falsify §1 itself |
| **B2** | ⭐⭐ **What is σ_fill, really?** Every constant rests on **four clean fills of one oil on one evening**. | §35 **T1**: five fills, one stock, same recipe, P6′ in force | turns the thresholds from *derived-with-a-gap* into *measured*; C5; the tracker's band |
| **B3** | ⚠ **How much light, for how long?** §39 reached "it is the light" by **elimination**, not measurement. | three aliquots drawn at once — one read immediately, one after 15 min dark, one after 15 min on the desk | nothing (the fix is free) — but it converts an elimination into a number |

### ⛔ C · NOT DERIVABLE FROM TODAY'S ARCHIVE — deliberately deferred

| # | question | why it is stuck | when to revisit |
|---|---|---|---|
| **C1** | a **level threshold** for "this fill never cleared" (run 002) | 002's terminal `A_valley` 0.204 is only **1.35×** the next highest — no cluster gap (§32.5) | after B2 |
| **C2** | **`theta_rel`** for a relative-rate gate | the twelve runs span 0.24–1.50 %/min at the read with no gap (§33.7/C5) | after B2 |
| **C3** | the history tracker's **per-oil threshold** | needs ≥5 fills **per oil**; the pooled 0.25–0.30 is the interim (§37.9) | after B2, per oil |
| **C4** | **is `D` worth anything against the case it exists for** — a genuinely different or adulterated oil? | ⛔ **no such sample is in the archive.** §37.7 only proved it separates two different oils, the weakest form | when a real adulteration/foreign sample exists |

### ⚠ D · OPEN SCIENCE — blocks nothing, and each is a real hole

| # | question |
|---|---|
| **D1** | ⛔ **The hump's lower limb has no model.** §32.4 explains the collapse above `A_valley ≈ 1.7` as the dark floor. Why `Q%` *rises* with turbidity from 0.06 to 1.7 is unexplained, and λ⁻ⁿ scattering predicts the **opposite sign** (§32.3, §33.3). ⇒ every turbidity statement in this file is empirical. |
| **D2** | ⚠ **What disturbed run 006 between t = 150 and 300 s?** Scatter 20× the tail, `A_valley` stalls, then everything returns to trend. The record says nothing, and §40 handles the symptom, not the cause. |
| **D3** | ⚠ **Why is the second aliquot consistently more dilute?** −23.8 % / −5.1 % / −6.7 % across three stocks. ⭐ It has **no `Q%` consequence** — which is dilution-invariance working exactly as designed — but the concentration difference itself is unexplained. |
| **D4** | ⚠ **Is the reference's ±3 % wander the lamp or the re-seating?** §38.6 downgraded it from "drift" to "wander"; separating the two needs §16.26's null-run design, not this data. |
| **D5** | ⚠ **Does any of this transfer to a second oil?** 5 of 7 Lugitsch fills arrive clear; 0 of 3 Billa fills do, and Billa clears ~5× slower. Every constant here is a Billa constant until a second oil runs the same series. |

### ⭐ 47.1 · WHAT IS **NOT** OPEN ANY MORE

⭐ Worth saying, because several of these consumed a whole exchange each:

- **"same stock?"** — answered: yes. **"which aliquot was 006?"** — answered: the second, measured first.
- **κ** — dead (§39.5: extrapolation triples the scatter, slopes disagree in sign).
- **the pour** — dead as a mechanism; it was **light on the waiting aliquot** (§39.2).
- **W5** — Edwin's call: not persisted. **W6 / `D2` live** — killed by measurement (§43/RD5).
- **the C2 hunt window** — dropped; C1 and §40 both catch its only case.
- **which read rule** — settled: the **drawdown** rule is the answer rule; `D2` is a shape test that cannot
  refuse a still-clearing run (§41.5).
- **is the history tracker blocked?** — no (§37.7). Buildable, but the scalar half is the valuable one.


### ⭐⭐ 47.2 · A5 DISSOLVED — the outcome enum needs nothing  *(2026-08-20, working it through)*

§43/RD7 asked for a new `PLANNED_END` member because *"the clock running out is the normal ending"*. ⛔ That
conflated **why the run stopped** with **what the answer is**. Walk the two cases at the planned end:

| at the 20-minute mark | outcome |
|---|---|
| finalize finds an admissible minimum | ⭐ `SETTLED_AFTER_CLEARING` / `SETTLED_IMMEDIATE` — **exactly as today** |
| finalize finds none | ⭐ `NEVER_SETTLED` — *"the run ended without settling, no value"*, which is **precisely right** |

⇒ ⭐⭐ **no enum member is needed, and no persisted string changes.**

⚠ The one thing worth keeping is the distinction between *"it ran its planned 20 minutes"* and *"it blew
through to the 25-minute guarantee"* — the second means the planned end failed to fire and something is
wrong. ⭐ **`capsHit` already exists** in `MonitorResult.toRecord()`; add a `plannedEnd` boolean beside it.

⭐ **A5 was the cheapest of the six and it turned out to cost nothing at all** — which is the argument for
walking a proposal through its cases before writing it down as a decision.

---

## ⭐⭐ 48 · A3 AND A4 — the leans, and a finding that reorders the phases  *(2026-08-20)*

### ⭐ 48.1 · A3 — as proposed, with two refinements found while checking it

| a run ends because… | lean | why |
|---|---|---|
| `decision.stop` — settled / degrading | ⭐ **yes** | and it is a **no-op today**: finalize sees the same row list the gate saw, so it re-derives the same answer. ⭐ That is what makes B4 a real checkpoint. |
| caps / the planned duration | ⭐ **yes** | the ending W7 exists for |
| `FAILED` | ⛔ **no** | the evaluator just raised; calling it again stacks a second traceback on the first and the record loses which one was the cause |
| `CANCELLED` | ⛔ **no** | §12.1. ⭐ And the stronger reason: *not calling it* makes "a cancelled run carries no number" true **by construction**, instead of relying on the host to remember to ignore one |
| `STALLED` | ⭐ **yes** — outcome unchanged | the rows that exist are real, and the operator cannot cheaply repeat a fill |

#### ⚠ Refinement 1 — a STALLED run's answer is RECORDED but NOT REPORTED

`MonitorOutcome.hasValue()` does not include `STALLED`. ⇒ a stalled run that finalize reads would carry an
answer the outcome says does not exist.

⭐ **Leave `hasValue()` alone.** The number lands in the `MonitorRecord` for later analysis and is **not**
presented as a measurement. That is the same treatment §12.1 gives a cancelled run's trajectory — evidence
kept, not promoted.

#### ⚠ Refinement 2 — the CANCELLED/STALLED asymmetry is deliberate, and must be written down

They look alike and are not: **cancel is the operator deciding this run does not count; a stall is the
instrument failing a run the operator still wanted.** ⇒ the trajectory is kept in both cases; only the stall
gets read.

### ⭐⭐ 48.2 · A4 — yes, revise once — **and buy the alternative's one real advantage anyway**

⭐ **Lean: allow exactly one revision, at finalize.**

1. §14.6's harm model is *the operator watches and the number creeps*. One re-read at a moment when no
   further data can arrive is not that.
2. The alternative — *the gate never promotes; only finalize may* — is conceptually cleaner but breaks five
   tests (§43/RD6), changes DIAGNOSTIC mode, and **throws away the gate-time answer**, which is what makes
   B4 a checkpoint and M2's skew visible.
3. The revision is never invisible: `readPhase` · `gateAnswer` · `gateSeconds` (§45/M7).

#### ⛔ But the alternative HAS one real advantage, and it should not be waved away

Under a core/plugin skew (§45/M2):

| | skew behaviour |
|---|---|
| **revise** | finalize is never called ⇒ the gate answer stands **silently** (006 back to 18.989) |
| **only finalize promotes** | finalize is never called ⇒ **no answer at all** — a loud failure |

⭐ The loud failure is genuinely safer. ⭐⭐ **And it can be bought without the alternative's costs:**

```
spectracsPy-core      MonitorEngine.SUPPORTS_FINALIZE = True
spectracs-plugins     createMonitor() refuses to build a monitor if the engine does not advertise it
```

⇒ **the skew then fails at the start of the run, loudly, before a drop of lamp is spent on it.** One line
each side, and it makes A4's proposal strictly better than the alternative rather than merely cheaper.

⚠ One behaviour change the operator will see and must be told about: **run 003 goes from "8.450" to no
answer at all.** That is correct, and it is still a change.

### ⛔⛔ 48.3 · THE FINDING — C IS SAFE WITHOUT E, AND NEARLY TOOTHLESS WITHOUT IT

Checking A3 meant asking how much evidence the drawdown test actually has. **It has almost none on most
runs**, because today's gate stops a run one or two rows after it confirms the minimum:

| run | rows after the chosen minimum | drawdown |
|---|---|---|
| 20260819/001 | 35 | 0.0076 |
| Billa 004 · 005 | 19 · 19 | 0.0197 · 0.0755 |
| Billa 006 | 13 | 0.0212 |
| Lugitsch 005 | 4 | 0.0097 |
| Lugitsch 004 | 3 | 0.0110 |
| Lugitsch 002 · 007, 20260818A | 2 · 2 · 2 | 0.0100 · **0.0000** · **0.0000** |
| **Billa 001 · Billa 007 · Lugitsch 001 · 006** | **1 · 1 · 1 · 1** | **0.0000** |

⛔⛔ **Eight of thirteen runs have fewer than four rows after their minimum, and six of those score
`drawdown = 0.0000` — admissible by ABSENCE of evidence, not by evidence.** The rule is right on the archive
(it moves only 006 and refuses 003) largely because the runs where it *mattered* happen to be the long ones.

⇒ ⭐⭐⭐ **E is not an optional nicety beside C. The fixed duration is what gives the drawdown rule anything
to look at.** Three consequences:

- ⭐ **E moves up the order** — it can land before or with C rather than last. It changes no answer, so
  moving it is free.
- ⭐ **C1 must record `rowsAfterMinimum`** beside `drawdown`, or a `0.0000` from one row is indistinguishable
  from a `0.0000` from nineteen.
- ⭐ **A4's revision only ever matters on a run long enough to have a tail** — which is the same argument
  again, from the other end.

⚠ And it re-prices §33.8's T0: the 60-minute run is not only *"is 20 minutes enough to settle?"* — it is
also *"how many rows does the read need after the minimum to mean anything?"*

---

## ⭐⭐ 49 · FINAL RUBBER-DUCK PASS — and it catches a cap wearing a costume  *(2026-08-20)*

⭐ Third and last pass. **Six findings; one would have broken the very first 20-minute run.**

### ⛔⛔ F1 — `maxFrames = 4000` IS A ~20-MINUTE CAP IN DISGUISE. THE FRAME CAP FIRES BEFORE THE CLOCK.

The archive's own frame rate, computed from `frameIndex` and `t`:

| run | fps | frames a 1200 s run would need | `maxFrames` |
|---|---|---|---|
| Billa 001 | **3.34** | ⛔ **4008** | 4000 |
| Billa 005 | 3.29 | 3950 | 4000 |
| Billa 006 | 3.28 | 3936 | 4000 |
| Billa 004 | 3.26 | 3918 | 4000 |
| Billa 007 | 3.23 | 3880 | 4000 |

⛔⛔ **Every archived run's rate puts a 20-minute run within 2 % of the frame cap, and one of them is already
over it.** `__enforceCaps` would fire on frames at ~19.9 minutes, set `capsHit = True`, and — with nothing
promoted, which is the normal state until finalize runs — finish as **`NEVER_SETTLED`**. ⇒ **the planned
ending would essentially never be reached, and the outcome would be wrong on every run.**

⭐ The diagnosis: `maxFrames` was set as a runaway guard and, at this camera's ~3.3 fps, it is *numerically*
a 20-minute limit. **It is a second time cap wearing a frame costume, and it happens to sit exactly where
the planned duration wants to be.**

⭐⭐ **Fix, and it is free** — `maxFrames` counts; it does not allocate (the ring is sized by
`windowFrames + retention`, not by `maxFrames`). Derive it instead of pinning it:

```
maxFrames  =  ceil( maxSeconds  x  ASSUMED_MAX_FPS )        ASSUMED_MAX_FPS = 10, stated, not guessed
           =  15000 at the 1500 s guarantee
```

⚠ And E1 must **assert `plannedSeconds x observedFps < maxFrames`** at construction, or the next camera
change silently reintroduces the same bug.

### ⭐⭐ F2 — E SOLVES §17/U3 AND §27.23. THE BAR CAN FINALLY BE DETERMINATE.

`CapturePanel` line 1002: `signal.stepsCount = 0` — the app-wide *"no knowable end"* convention, and §27.23
had to design a stripe-less INDETERMINATE bar around it because **nothing could predict when a gated run
would finish.**

⭐ **A planned duration is a knowable end.** ⇒ `stepsCount` becomes real, the bar fills honestly, and
§17/U3's complaint — *"the cap is a 25-minute silence ending in nothing"* — is answered by construction.

⚠ Keep the INDETERMINATE path: it is still right for a `tooDark` opening (§43/RD3 — nothing to predict from
while no row produces a metric) and for a plain burst.

### ⚠ F3 — `finalize()` RUNS INSIDE `offer()`, ON WHOEVER'S THREAD PUMPS FRAMES

`__enforceCaps()` → `__finish()` → `finalize()`, and `__enforceCaps` is called from `offer()`. ⇒ the
end-of-run read executes on the frame-delivery thread. ⭐ The work is small — one pass over ≤ 70 rows and a
three-point polyfit — but it must **stay** small, and it must never raise: §25/X5's guard covers `decide()`,
and finalize needs the same `try/except → FAILED` treatment.

### ⭐ F4 — THE RETENTION ARITHMETIC IS SAFE, EVEN AT `plannedSeconds == maxSeconds`  *(checked, not assumed)*

`__pruneSpectra` computes `horizon = newest - maxSeconds`. At the end of a 1200 s run with `maxSeconds`
1500, `horizon = -300` — everything kept. Set `maxSeconds` to 1200 as well and `horizon = 0`, while the
first row's `t` is ~6 s — **still everything kept.** ⭐ No spectrum can be pruned before finalize reads it.

### ⚠ F5 — §17/U4 GETS WORSE BEFORE IT GETS BETTER

*"Twenty minutes is a long time to hold a panel hostage"* was written when runs were 2–14 minutes. E makes
every run 20. ⭐ Three things already exist and should be named in the same breath: cancel works (§12.1), the
bar becomes determinate (F2), and the coach line says what the fill is doing. ⛔ **Do not ship E without F2**
— a 20-minute wait behind a stripe-less bar is a materially worse bench than a 6-minute one.

### ⭐ 49.1 · WHAT THIS PASS DID **NOT** FIND — and why it is the last one

Checked and clean: the record path (`CapturePanel:902`, one line, unchanged for A–D) · the serialisation
(`answer` and `rows` ride wholesale, no migration) · the test doubles (plain classes, §45/M3) · the lint
(`plugin_sdk` imports are permitted) · the android copy (a 269-line spike stub) · the ring sizing
(`FrameRing`'s own W + max(5, W//5) rule) · `evaluateEveryNFrames = 1` at 3.3 fps (~3900 evaluations, the
same load as today).

⭐ **Three passes have now returned: a missing seam (§43), a silent skew and two undecided rules (§45), and
one cap in a costume (§49).** The yield is falling and the remaining risk is no longer in the code — it is in
**four clean fills of one oil on one evening** (§35's T1). ⇒ **stop ducking, start typing, and let the rig
supply the next correction.**

---

## ⭐⭐⭐ 50 · THE PHASES — FINAL  *(supersedes §44 and §46; DESIGN, nothing built)*

⭐ Changes from §46: **E moves up to sit beside C** (§48.3 — the drawdown rule is starved without it),
**A2 and A5 are closed**, and **F1's frame cap joins E1**.

```
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| STEP | WHAT                                            | REPO              | SIZE | ANSWERS   | GREEN?   |
+======+=================================================+===================+======+===========+==========+
|                      PHASE 0  ·  BEFORE A LINE IS WRITTEN                                                |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| 0.1  | Is a SEALED dev.DevSpectralPlugin row in the DB?| server DB query   |  --  |   none    |   n/a    |
|      | If yes the FILE is ignored at the rig.  ** M1 **|                   |      |           |          |
| 0.2  | A3 - finalize on cancel / stall / failure       | Edwin             |  --  |   none    |   n/a    |
| 0.3  | A4 - may finalize REVISE a latched answer       | Edwin             |  --  |   none    |   n/a    |
|      | (the §14.6 amendment)                           |                   |      |           |          |
|      | A2 tailSd on <8 rows .............. CLOSED  ok  |                   |      |           |          |
|      | A5 planned-end outcome ....... DISSOLVED §47.2  |                   |      |           |          |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      PHASE A  ·  HARNESS AND RECORDING              no answer moves                      |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| A1   | replay FIXTURE: rows of all 16 runs + the       | spectracsPy/tests |  M   |   none    |   yes    |
|      | RECOMPUTED clearing-2.0 answer        ** RD9 ** |                   |      |           |          |
| A2   | replay TEST over the real decide()              | spectracsPy/tests |  S   |   none    |   yes    |
| A3   | W1: three band rates -> diagnostics + one line  | spectracs-plugins |  S   |   none    |   yes    |
|      | on the report (PDF and bench)                   |                   |      |           |          |
| A4   | W4: clearingObserved, A_valley at the read,     | spectracs-plugins |  S   |   none    |   yes    |
|      | the reference band means                        |                   |      |           |          |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      PHASE B  ·  THE SEAM                           no answer moves                      |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| B1   | finalize(rows) probed from __finish(); the A3   | spectracsPy-core  |  S   |   none    |   yes    |
|      | path set; try/except -> FAILED       ** F3 **   |                   |      |           |          |
| B1b  | MonitorEngine.SUPPORTS_FINALIZE = True, and     | core + plugins    |  XS  |   none    |   yes    |
|      | createMonitor() REFUSES without it   ** M2 **   |                   |      |           |          |
| B2   | readPhase / gateAnswer / gateSeconds;           | core + plugins    |  XS  |   none    |   yes    |
|      | the §14.6 LATCH AMENDMENT written down          | + spec            |      |           |          |
| B3   | ClearingEvaluator.finalize() = today's __read() | spectracs-plugins |  S   |   none    | yes <== |
|      | over the WHOLE row list                         |                   |      |           | CHECKPT |
| B4   | A2 also asserts readPhase == "final"            | spectracsPy/tests |  XS  |   none    |   yes    |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      PHASE E  ·  THE CLOCK   (moved UP - §48.3)     no answer moves                      |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| E1   | MonitorPolicy.plannedSeconds (<= maxSeconds),   | spectracsPy-core  |  S   |   none    |   yes    |
|      | AND maxFrames = ceil(maxSeconds x 10 fps),      |                   |      |           |          |
|      | AND assert plannedSeconds x fps < maxFrames     |                   |      |           |          |
|      |                                      ** F1 **   |                   |      |           |          |
| E2   | plannedEnd boolean beside capsHit; the outcome  | core + plugins    |  XS  |   none    |   yes    |
|      | still comes from finalize        ** §47.2 **    |                   |      |           |          |
| E3   | the gate runs on underneath; record when it     | spectracs-plugins |  XS  |   none    |   yes    |
|      | WOULD have fired                                |                   |      |           |          |
| E4   | DETERMINATE progress bar (stepsCount from       | spectracsPy       |  S   |   none    |   yes    |
|      | plannedSeconds); INDETERMINATE kept for tooDark |                   |      |           |          |
|      | and bursts            ** F2 - ship WITH E **    |                   |      |           |          |
| E5   | the duration control, default 20 min            | spectracsPy       |  S   |   none    |   yes    |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      PHASE C  ·  THE READ                           TWO answers move                     |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| C1   | W2: drawdown(i) <= 10 x tailSd; answer = vertex | spectracs-plugins |  M   | 006, 003  | ** RED **|
|      | at the DEEPEST admissible minimum. Keep the     |                   |      |           | until C2 |
|      | far-side guard. A2's <8-row rule.               |                   |      |           |          |
| C2   | fixture: EXACTLY two rows move                  | spectracsPy/tests |  XS  |    --     |   yes    |
|      | 006 18.989 -> 19.782 ;  003 -> refused          |                   |      |           |          |
| C3   | record drawdown, tailSd, tailRows,              | spectracs-plugins |  XS  |   none    |   yes    |
|      | rowsAfterMinimum, and the REJECTED candidates   |                   |      |           |          |
|      |                                     ** §48.3 ** |                   |      |           |          |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      PHASE D  ·  THE INPUT GUARD                    no answer moves                      |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| D1   | MONITOR_SORET_CEILING (its OWN constant, M6)    | spectracs-plugins |  S   |   none    |   yes    |
|      | -> {"tooDark": 1.0}; decide() filters first;    |                   |      |           |          |
|      | MEASUREMENT_BROKEN counts empty values only     |                   |      |           |          |
| D2   | no spectrum attached to a tooDark row           | spectracs-plugins |  XS  |   none    |   yes    |
| D3   | coach "too dark to read - still clearing";      | spectracs-plugins |  XS  |   none    |   yes    |
|      | the bar goes INDETERMINATE while it lasts       |                   |      |           |          |
| D4   | fixture: 9/12 untouched; 006L and Billa 001     | spectracsPy/tests |  XS  |   none    |   yes    |
|      | lose opening rows; Billa 003 loses its first 21 |                   |      |           |          |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
|                      NOT IN ANY PHASE                                                                    |
+------+-------------------------------------------------+-------------------+------+-----------+----------+
| W5 persist the last row's spectrum   | Edwin's call, §43/RD10                                            |
| W6 D2 as a live check                | killed by §43/RD5 - never fires on a running scale                |
| the A_valley hunt window             | §42.8 - no case left; a rule with no case can only misfire        |
| kappa / theta_rel / C3-as-verdict /  | §42.8 - not derivable from today's archive; revisit after T1      |
| C6 / P8 / the history tracker        |                                                                   |
+------+-------------------------------------------------+-------------------+------+-----------+----------+

 SIZE: XS <20 lines · S 20-60 · M 60-150      LANDING ORDER: core -> plugins -> app tests   (M2: a skew
                                              fails silently, and B1b is what makes it fail loudly)
```

### ⭐ 50.1 · READ THE TABLE TWO WAYS

- ⭐ **Down the ANSWERS column:** every phase says *none* except **C**, which says *006 and 003*. That is the
  whole safety argument, and **A2 — written first — is what turns it from a claim into a test.**
- ⭐ **Down the GREEN column:** one red cell, **C1**, red on purpose and for exactly one commit, because the
  fixture that defines correctness is the thing being changed.

---

## ✅⭐⭐ 51 · AS BUILT — phases 0 · A · B · E · C · D, 2026-08-20  *(511 tests green, was 460)*

⭐ All five phases landed. **Only phase C moved a number, and it moved exactly the two §46 predicted.**

### ⛔⛔ 51.0 · PHASE 0 — M1 WAS A REAL HAZARD, AND THE ANSWER IS "THE FILE IS LIVE"

`~/.spectracsPy-server/spectracsPyServer.db` **does** carry a sealed row:

```
title    Measurement bench (dev) (DB)
codeRef  sciens.spectracs.plugins.dev.DevSpectralPlugin.DevSpectralPlugin
version  1.1.0     source 17,218 chars     signed, keyId 0c618b47f8a17f36
```

⛔ **That source contains none of the settling machinery** — no `ClearingEvaluator`, no `createMonitor`, no
`monitorMetrics`, no `V_THRESHOLD` — against the live file's **153,100 chars**. It is a stale seed from
before the settling work.

⭐ **The bench is nonetheless running the FILE**, proven by the runs themselves: 006 and 007 carry
`monitorRecord`s stamped `evaluatorId: "dev-clearing"`, which only the file can produce. ⇒ the edits below
take effect.

⚠ **But the stale row is a live trap**: assign v1.1.0 to any user and the bench silently loses the entire
settling feature. **Edwin's call** — delete it, or re-publish from the current file.

### ✅ 51.1 · WHAT LANDED

| | | repo |
|---|---|---|
| **A1/A2** | `tests/data/monitor_replay.json` — sixteen runs, 379 rows, `expected` recomputed and pinned — plus `test_monitor_replay.py`, 34 tests | spectracsPy |
| **A3** | the three band rates as `%/min` in `__stateAtRead`, and a *"⚠ still clearing / settled?"* line on the Settling view and the report | spectracs-plugins |
| **A4** | `clearingObserved` · `valleyAtRead` · `valleyAtEnd` · `referenceSoret/Valley/Q` | spectracs-plugins |
| **B1** | `MonitorEngine.__finalRead()` from `__finish()`, with §48.1's ending set and §49/F3's guard | spectracsPy-core |
| **B1b** | `MonitorEngine.SUPPORTS_FINALIZE`; `createMonitor()` **raises** without it | core + plugins |
| **B2** | `readPhase` · `gateAnswer` · `gateSeconds`; `MonitorDecision.withdraw` | core + plugins |
| **B3** | `ClearingEvaluator.finalize()` → the same `__read()`, over the whole row list | spectracs-plugins |
| **E1** | `MonitorPolicy.plannedSeconds`, and ⭐ **`maxFrames` now DERIVED** — `maxSeconds × ASSUMED_MAX_FPS` | spectracsPy-core |
| **E2** | `plannedEnd` beside `capsHit`; ⭐ **no new outcome member** (§47.2) | core + plugins |
| **E4/E5** | a **determinate** status bar against `plannedSeconds`; `MONITOR_PLANNED_SECONDS = 1200` | app + plugins |
| **C1/C3** | `drawdownAfter` · `tailSd` · `__admissibleMinimum`, and the rejected candidates in the record | spectracs-plugins |
| **D1–D3** | `MONITOR_SORET_CEILING` → `{"tooDark": 1.0}`; filtered first in `decide()`; the coach line | spectracs-plugins |

### ⭐⭐ 51.2 · THE ANSWERS THAT MOVED — exactly two, as promised

```
20280819BillaClever/003    8.450  ->  NO ANSWER      (every turning point was followed by a further fall)
20280819BillaClever/006   18.989  ->  19.7822        (= Edwin's (1), t = 412.9 s)
```

⭐ **Fourteen of sixteen bit-identical**, including the five runs the ceiling touches. And
`test_series_f_replay.py` — written months earlier and untouched here — still passes every one of its
assertions but the version literal, which is independent evidence that B3 was a pure refactor.

### ⛔⛔ 51.3 · THE HARNESS EARNED ITSELF ON ITS FIRST RUN — THREE FINDINGS

**1 · `evaluatorVersion` is a lie in the archive.** `20260818A/001` is stamped `clearing-2.0` and prints
**28.321** (a VERTEX); today's 2.0 replays it to **28.569** (the first look), because **TEST C landed on
2026-08-19 without bumping the string**. ⇒ *"clearing-2.0" identifies two different algorithms.* §29.6 and
§30.12 set that string up as the one thing that says which rule produced a number, and it silently stopped
doing so. ⭐ **Bumped to `clearing-3.0` here, and `test_series_f_replay` asserts the literal so the next bump
must be a visible act.**

**2 · "no turning point at all" is not a refusal.** The first cut of `__admissibleMinimum` conflated *"no
candidates"* with *"all candidates rejected"* and refused **Lugitsch 003 and Billa 002** — two perfectly
good monotone runs whose answer is the first look. A monotone curve belongs to the depth test, not to §40.

**3 · A finalize that refuses must WITHDRAW the gate's answer.** Without it, run 003 kept the 8.450 the
end-of-run read had just judged unsound — §32.2's defect surviving the fix written for it. `withdraw` is now
an explicit field, and the engine clears the answer, the spectrum and the winning row while keeping the
trajectory.

⚠ All three were found by the harness within minutes of it existing, which is the argument for A2 going
first.

### ⚠ 51.4 · CORRECTIONS TO THE SPEC, FROM THE BUILD

- ⚠ **§32.4's ceiling table was stale.** It was written before runs 004–007 existed. Measured now: the
  ceiling touches **five** runs, not three — Lugitsch 006 (5 rows), Billa 001 (2), **Billa 003 (21)**, Billa
  005 (6), Billa 006 (1). ⭐ **And it costs none of them an answer except 003**, which is the point.
- ⭐ `MonitorPolicy.maxFrames` **defaults to `None` now** and derives itself. An explicit value is still
  honoured, and §49/F1's assertion rejects one that would pre-empt the planned duration.

### ⏸ 51.5 · WHAT IS STILL OWED

| | |
|---|---|
| ⏸ **the rig click-through** | none of this has run against a camera. E4's determinate bar and D3's coach line are the two that only the bench can verify. |
| ⏸ **the stale sealed row** | §51.0 — Edwin's call |
| ⏸ **T0 / T1** | the 20 minutes is provisional, and every constant still rests on four clean fills of one oil on one evening |
| ⛔ **not built, by decision** | W5 (§43/RD10) · W6 (§43/RD5) · the hunt window · κ · θ_rel · C3-as-verdict · the history tracker |

---

## ⭐⭐ 52 · THE WHITE-SPIRIT SESSION, READ AS A TEST OF THE GATE — and it finds a failure mode the gate cannot see  *(Edwin 2026-08-20/21, four measurements; `SPEC_capture_quality.md` §16.12.7f is the solvent half)*

§16.12.7e ended with a claim about this subsystem: *"if the hydrocarbon works, the settling subsystem's last
job is to prove itself unnecessary."* Four fills ran. ⛔ **It did not prove itself unnecessary. It proved it
has a blind spot**, and this section is that.

⚠ **Language first**, because §51 and everything before it got it wrong for two days: the archive is **oil in
isopropanol** (§16.23 — two 60 µL capillaries into 10 mL), not neat oil. Every "IPA" below is the shipping
route; every "spirit" is the new one.

### ⭐ 52.1 · THE FOUR RUNS, AS THE MONITOR SAW THEM

| run | outcome | read | `Q%` | `A_valley` at read | browning /min |
|---|---|---|---|---|---|
| Lugitsch `001` | `SETTLED_IMMEDIATE` | `FIRST_SETTLED_WINDOW`, t = 6.1 s | 20.789 | 0.1428 | 0.114 |
| Lugitsch `002` | `DEGRADING_FILL` | `VERTEX`, t = 91.0 s, depth 0.344 | 20.623 | 0.1217 | 0.066 |
| Billa `001` | `SETTLED_IMMEDIATE` | `FIRST_SETTLED_WINDOW`, t = 6.7 s | 21.832 | **0.2647** | 0.400 |
| Billa `002` | `SETTLED_IMMEDIATE` | `FIRST_SETTLED_WINDOW`, t = 6.8 s | 22.038 | 0.1554 | 0.217 |

⭐ **§31's TEST C machinery fired correctly on Lugitsch `002`** — four `gate held` notes on a rising
`A_valley`, then the coarsening warning, then `DEGRADING_FILL` with a vertex read and *"a fresh dilution is
needed"*. ⭐ **The read rule was right on all four**, and `clearing-3.0` needed no change.

### ⛔⛔ 52.2 · THE BLIND SPOT — a turbid, still-clearing fill is classed `arrived-clear`

Billa `001` was read at **t = 6.7 s, its most turbid moment**, on the `arrived-clear` branch, while
`A_valley` was **still falling** (0.2647 → 0.2526 over 140 s, `clearingObserved` **+0.0455**). Its
`A_valley` of **0.2647 is the highest in the whole archive** outside the opaque `20280819BillaClever/003`.

⛔ **The gate could not see it, and the reason is structural: `Q%` is pedestal-blind by construction.** A
flat pedestal `b` cancels exactly in `V`'s numerator, `(A_Q + b) − (A_valley + b)`. The monitor watches
`Q%`. ⇒ **a fill can be as turbid as you like and still look "arrived-clear" to the monitor**, provided the
turbidity is grey. §31's TEST C only catches `A_valley` **rising**; here it was *falling*, from a start that
should have been refused outright. **There is no absolute `A_valley` ceiling anywhere in the gate.**

⇒ ⭐⭐ **This is the evidence §42's W3 was spec'd on, and it promotes W3 from an improvement to a
prerequisite.** The threshold suggests itself from the data: every clean fill on record sits at
`A_valley ≤ 0.21`; this one sat at 0.2647. ⛔ W3 must be an **absolute** refusal, not another rate test.

### ⛔ 52.3 · WHY THE `Q%` AGREEMENT ON BILLA CLEVER IS LUCK, NOT ROBUSTNESS

The two Billa fills agree to **0.206** — better than that oil's own IPA fill-to-fill sd of 0.699. ⛔ **Do not
read that as the metric surviving the bad fill.** Fitting one spectrum against the other over 490–630 nm:

```
 A_001 = 1.1631 * A_002 + 0.0776       resid 0.0160     <- a FLAT pedestal of +0.078 A
```

Two large errors cancelled:

| | |
|---|---|
| the pedestal cancels in `V`'s **numerator** and survives only in the **denominator**, inflating `A_Soret` by +0.078 | `Q%` depressed ~8 % — **remove it and `001` reads 23.71, not 21.85** |
| working against it, `001`'s Soret is **compressed** — the affine fit predicts `A_Soret` 0.9893, measured **0.9295** — because `A448` = 1.671 is into the nonlinear top of the range | `Q%` inflated |

+0.078 and −0.060 leave 0.018 on a ~0.99 denominator. ⇒ **the 0.206 is the residue of two errors an order of
magnitude larger.** A turbid fill that had *not* also saturated the Soret would have read ~1.9 units out.

⭐ **What did report the damage honestly**, on the same pair: `Greenness G` 0.891 vs 1.330 (+49 %), `Pigment
ratio · clarity` 3.687 vs 5.291 (+43 %), `Clarity A_green` 0.268 vs 0.158 (−41 %), `Intrinsic` hue 286° vs
297°. ⇒ ⛔ **`Q%` agreement is not a fill-quality check. `A_valley` and `Pigment ratio · clarity` both
flagged this pair loudly; `Q%` did not.**

⚠ **And the contrast with Lugitsch is the cleanest thing in the session:**

```
 Lugitsch     A_001 = 1.1590 * A_002 + 0.0052      resid 0.0059    <- pure SCALE
 Billa Clever A_001 = 1.1631 * A_002 + 0.0776      resid 0.0160    <- scale + pedestal
```

Same multiplicative term (1.159 / 1.163 — the two capillaries differ by ~16 %, a property of the vessels).
**The pedestal is the whole difference between "dissolves perfectly" and "dissolves imperfectly."**

### ⭐ 52.4 · THE DOMAIN GUARD FIRED, ON REAL DATA, FOR THE SECOND TIME

Billa `002` printed **no `Verdict · Q%` pill at all.** Its 22.038 is past
`DevSpectralPlugin.V_VERDICT_BAND = (12.0, 22.0)`, so `DevSpectralPlugin.py:2210` withheld it — numbers and
plot intact, verdict withheld, exactly as §51's comment says it should. ⭐ **After the 8.45 case, this is the
second time the guard has caught a real run**, and the first time it caught one for being too *high*.

⇒ ⚠ **It also says the white-spirit route pushes this oil out the top of the metric's declared scale.** The
band was drawn on the isopropanol corpus. ⛔ Not a reason to widen it — a reason not to read `Q%` across a
solvent change at all (§16.12.7f).

### ⚠ 52.5 · THE POUR, IN THE OTHER SOLVENT

Both pairs are **first 4 mL vs second 4 mL of one dilution** — §36.2's pour variable, unplanned.

| | first → second pour |
|---|---|
| isopropanol, stock 1 (§36.2) | **+0.444** |
| isopropanol, stock 2 (§36.2) | **+0.803** |
| **white spirit, Lugitsch** | **−0.166** |
| **white spirit, Billa Clever** | +0.206 ⚠ *(and §52.3 says this number means nothing)* |

⭐ **On the oil that dissolves, the pour term collapses and flips sign** — consistent with §36.2's own
reading that the second pour drags a heavier settled fraction, which a true solution does not have. ⛔ **Two
fills, one oil, one evening. This does not retire P6.** §36.2's requirement that two fills are comparable
only from the same pour position stands until a designed repeat says otherwise.

### ⏸ 52.6 · WHAT THIS ADDS TO THE OWED LIST

| | |
|---|---|
| ⭐⭐ **W3 becomes a prerequisite** | an **absolute** `A_valley` ceiling, not a rate test. Clean fills ≤ 0.21; this one 0.2647 |
| ⭐⭐ **W8 — NEW, 2026-08-21** | record `A(563–573)` and `A(623–626)` as `MONITOR_COLUMNS`. ⛔ **Prerequisite** for anything `dQ100`-shaped and ⛔ **not retroactive** — see §52.7 |
| ⚠ **re-specify §16.12.7e's arm-A gate** | `A_valley` alone cannot answer "is it clear?" across a solvent change — the solvent moves the pigment's own 500–630 absorbance 1.5–2.0× (§16.12.7f) |
| ⚠ **a fill-quality check that is not `Q%`** | `Pigment ratio · clarity` and `A_valley` both worked here; `Q%` did not |
| ⛔ **unchanged** | `clearing-3.0` read all four runs correctly and needs no edit |
| ⏸ **still owed from §51** | the rig click-through, the stale sealed row, T0/T1 |

### ⭐⭐ 52.7 · WHAT THE METRIC DECISION OF 2026-08-21 DOES TO THIS SUBSYSTEM — and it is less than it looks

`dQ100` replaced `Q%` as the main metric that day (`SPEC_metric_research.md` §12.8, roadmap *DECIDED
2026-08-21*). The obvious next move is to repoint `ClearingEvaluator` at it. ⛔ **Do not, yet.**

#### ⛔ 52.7a · No `dQ100` settling curve has ever been observed

`MONITOR_COLUMNS` carries `qPercent · soret(448–460) · valley(500–560) · qBand(565–580)`. **Neither
`A(563–573)` nor `A(623–626)` exists in any run ever taken**, and `qBand`'s window is the wrong one — it
straddles the 581 nm crossover (`DOC_lamp_rebuild.md` §6.1). ⇒ `dQ100` **cannot be reconstructed from a
`MonitorRecord`**, not for the 2026-08-21 runs and not for anything in the archive.

⇒ **W8 is a prerequisite, and it is not retroactive.** Every run taken before it lands is permanently
un-analysable for `dQ` trajectories. ⚠ It should go in **before the next lab session**, or that session's
runs will be as un-analysable as this one's.

#### ⚠ 52.7b · Theory and evidence disagree about what that curve looks like

| | |
|---|---|
| **theory says** | `dQ100`'s numerator is a difference, so a flat pedestal cancels, and `sd` is offset-blind ⇒ **clearing is invisible to it** ⇒ flat, then rising as the 624 band collapses ⇒ **no minimum**, the first look is the answer, and §40's drawdown, §41's `D2`, the hunt and the vertex read are all simply **inapplicable** |
| **the data said** | per-session correlations against `A_valley` as high as `r = −0.94` ⇒ it may well **have** a clearing limb |

⭐ **R1 has since weakened the second column considerably** (§12.11): the pooled *within-session* turbidity
coefficient is only **−21.4 with `r = −0.13`**, and the per-session slopes scatter from −718 to +75 — a
large `r` on six points with a small real slope. ⛔ But "weakened" is not "measured": R1 is cross-sectional,
and **nobody has watched `dQ100` move through a clearing curve.**

⇒ **W8 plus ONE monitored fill (roadmap R2) decides it**, and it is the *designed* version of R1:

```
   flat-then-rising  ->  read the FIRST look; do not apply the vertex machinery to dQ.
                         ⭐ NOTHING IS DELETED — Q% keeps its gate and its rules.
   V-shaped          ->  the existing vertex / drawdown rules transfer UNCHANGED;
                         only the column the evaluator reads changes.
```

#### ⭐ 52.7c · What does NOT change

- **`Q%` keeps driving the gate.** §51 shipped it, 511 tests are green, and §52.1 shows `clearing-3.0` read
  all four white-spirit runs correctly. ⛔ No read-rule edit is implied by the metric decision.
- **`Q%` keeps its `MonitorRecord` column and its metric row.** It loses only its **gauge** — the report
  must never show two verdict pills that contradict each other, and on the Spar session they disagree on 5
  of 6 runs (`SPEC_metric_research.md` §12.2).
- **W3 is metric-independent.** It refuses a fill that should not be measured at all, whichever number is
  read off it — and §52.3 shows it is `R` and `(3)/(2)` that the turbid fill would have destroyed, not
  `Q%` or `dQ100`. That is an argument for the ceiling, not against it: we cannot know in advance which
  metric a stored run will later be re-analysed with.
