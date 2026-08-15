# SPEC — ONE FILL, ONE WAIT, ONE BEST MEASUREMENT

> **Status: DESIGN, 2026-08-15. No code written. ⭐ HIGHEST PRIORITY — it precedes the σ_fill run, the
> refill test and the lamp rebuild**, because every one of those is an attempt to measure something
> stable, and until this lands the instrument does not produce one.
>
> Evidence base: `SPEC_capture_quality.md` §16.36 (the lamp changes the sample), §16.34.3d (the σ_fill
> design change), `SPEC_metric_research.md` §10. Prototype and every number below:
> `diagnostics/clearing_time_course.py`.

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

⛔ **Never take more captures than needed.** Every capture is light, and light is damage. Stop when the
minimum is confirmed. ⚠ At production dose this is ~1–2 % of a diagnostic run, which is why
§16.36.4 concludes this is not a product problem — but only if the device stops.

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

## 8 · Related

| topic | where |
|---|---|
| the two processes, and the controls behind them | `SPEC_capture_quality.md` §16.36 |
| what it re-weights — "the same oil" was not the same oil | §16.36.8 |
| the σ_fill design change it forces | §16.34.3d |
| `Q%`, the guards, the frozen windows | `SPEC_v_metric_integration.md`, `SPEC_metric_research.md` §10 |
| the working prototype | `diagnostics/clearing_time_course.py` |
| the shutter this would unblock, and the cloud point that forces it | `SPEC_capture_quality.md` §16.36.7 |
| the optical path a heater must not disturb | `SPEC_lamp_rebuild.md` §12.5 |
