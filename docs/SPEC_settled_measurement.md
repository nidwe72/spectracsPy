# SPEC — ONE FILL, ONE WAIT, ONE BEST MEASUREMENT

> **Status: DESIGN, 2026-08-15. No code written. ⭐ HIGHEST PRIORITY — it precedes the σ_fill run, the
> refill test and the lamp rebuild**, because every one of those is an attempt to measure something
> stable, and until this lands the instrument does not produce one.
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
| **σ_fill / the refill test** | it measures the reproducibility OF A MEASUREMENT. Until the measurement is defined, it measures the protocol's own drift — §16.34.3d |
| **the DIY lamp rebuild** | a new lamp changes the scale by 4.84 units (§10.4). Re-deriving thresholds on a drifting measurement bakes the drift into the new scale |
| **the internal PDFs** | they would document numbers the next protocol supersedes |
| **PRIO 3a ground truth** | labels compared against a measurement that moves are labels compared against nothing |

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

### ⭐ 29.3 The rule

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

### ⭐ 29.7 Phased

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
