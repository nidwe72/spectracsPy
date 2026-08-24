# SPEC — Colour retrieval from the spectrum (five chips + HSL)

Status: **IMPLEMENTED 2026-07-19 (K1–K4 built, K5 rig "works so far"; see §4 as-built).** Settled with Edwin 2026-07-19. Scope = the
**DEV plugin** (measurement bench) for now; the machinery (colour util + `MetricFieldView` + renderers) is generic and
any plugin can reuse it. Pairs with [`SPEC_capture_quality.md`](SPEC_capture_quality.md) (fidelity — now good enough to
trust colour) and the evaluation/colour pipeline in `spectracsPy-core`.

⭐ **§7 (2026-08-23) — DESIGN + AS BUILT (§7.13, 579 tests green).** It attributes §1c's *"every channel overlaps"* to three
properties of the converter — luminance dropped, gamut clamping, a fabricated red tail — prices the cost
(**ΔE00 28.8 discarded; two different oils printing identical H/S/L**),
specifies a fix, and then shows that the fix restores **fidelity, not discrimination**: colour as a channel
is currently a turbidity meter, and §7.6 is the evidence. ⛔ **The duck at §7.10 refuted two of the six proposed
findings** — in particular, **dropping luminance is the MECHANISM of dilution-invariance (§0, F8), not a defect**;
only the gamut clamping is. The corrected proposal is **§7.11** (add a sixth chip, don't change the five) and the
phases are **§7.12**.

**Purpose:** turn the measured spectrum into colour(s) the operator can *read* and the report can *print* — and, past
the human-visible colour, expose the **dilution-invariant intrinsic colour** so "this oil is too green / too brown"
becomes a stable signal rather than one that drifts with how much oil was in the cuvette.

---

## 0. The physics that forces the design (why one colour is not enough)

Beer–Lambert, changing the amount of oil `c·l → k·(c·l)`:

```
Absorbance:    A(λ) = ε(λ)·c·l   →   A → k·A          (pure SCALE)
Transmission:  T(λ) = 10^(−A)    →   T → T^k          (a POWER — a SHAPE change)
```

The colour pipeline (§2) integrates the spectrum to CIE **chromaticity `xy`** (luminance is dropped at `XYZ_to_xy`), so
the *whole* colour (H, S and L) comes from chromaticity:

- **Absorbance** scales by `k` ⇒ `X,Y,Z` all ×k ⇒ `xy` **unchanged** ⇒ the colour is **fully dilution-invariant.**
- **Transmission** is raised to `T^k` ⇒ its **shape** changes ⇒ `xy` **shifts** ⇒ the colour **moves with dilution.**
  *This is the pumpkin dichromatism* — thin oil transmits green, thick oil goes red, same oil.

So the perceived (transmission) colour is the human "what it looks like now" — reproducible only at a **fixed prep**
(Edwin's 3 ml alcohol + 2 drops), and it still tracks oil *quality* at fixed prep. The absorbance colour is the
**prep-proof intrinsic character**. We show **both**, each in a natural and a hue-only form, **plus** a hue-complemented
intrinsic chip that reads in the perceived green-yellow-brown family (§1a) → **five chips**.

---

## 1. The five chips (SETTLED)

Rendered by the DEV plugin **in this order** (Edwin), as a labelled colour group above the ratio metrics:

| Order | Code name | Friendly label | Source | S, L | Dilution |
|---|---|---|---|---|---|
| 1 | `colorIntrinsicPerceived` | **Intrinsic (perceived-family)** | absorbance, **hue+180°** | **fixed** S=0.80, L=0.50 | invariant |
| 2 | `colorAbsorbedNormalized` | **Intrinsic · hue only** | absorbance | **fixed** S=0.80, L=0.50 | invariant |
| 3 | `colorPerceivedNormalized` | **Perceived · hue only** | transmission | **fixed** S=0.80, L=0.50 | hue shifts with dilution |
| 4 | `colorAbsorbed` | **Intrinsic** | absorbance | natural (chromaticity-derived) | invariant |
| 5 | `colorPerceived` | **Perceived** | transmission | natural (chromaticity-derived) | shifts with dilution |

- **"Normalized"** = keep the measured **hue**, force **S=0.80 / L=0.50** → a vivid, comparable hue chip (green↔brown
  pops; not washed out by low saturation or a dark sample).
- **Natural** (#4/#5) = the colour as the pipeline produces it. See §3-F5: the "natural L" is the converter's lightness
  for that chromaticity, **not** the sample's real brightness — the normalized chips are the readable ones.
- **Full H/S/L is shown for all five** (Edwin), as a **read-only field to the RIGHT of each swatch**. For the
  normalized/intrinsic-perceived chips the S/L read the fixed constants (80 / 50) — shown anyway.
- **Labels:** friendly label visible; the exact code name + a one-line meaning go in the label's tooltip (traceable on
  the bench, readable for a human). *Overridable.*

### 1c. ⚠ MEASURED 2026-07-27 — the chips are a VISUAL AID, not a discriminator (on this oil pair)

> ⛔ **See §7 (2026-08-23) before using this section.** Its *verdict* stands — the chips do not discriminate — but its
> *diagnosis* is refuted. The difference is not lost to dilution; it is discarded by the converter (ΔE00 28.8 present
> in the spectra, printed as identical H/S/L). §7.4 says exactly what §1c got right and what it got wrong.

All nine renderable colour channels were scored against the 25 green/brown runs of 2026-07-27, leave-one-**fill**-out
(full table: [`SPEC_capture_quality.md`](SPEC_capture_quality.md) §16.10.15). **Every channel overlaps.** Best
\|d\| = 0.84 (absorbed lightness / chroma) against the linear-baseline pigment ratio's 2.88; best colour LOFO
score 10/25 against the ratio's 1/25.

Three findings that bear on the design above:

1. **Saturation reads exactly 100.0 on every run**, absorbed *and* perceived — the §3 F10 problem in the live
   data, not a corner case. The "natural" S in rows 4/5 of the table is therefore **structurally constant** and
   carries no information; only hue and (via chroma) lightness vary. Worth deciding whether to display it.
2. **Rows 1 and 2 are the same number.** `colorIntrinsicPerceived` = `colorAbsorbed` hue + 180° by construction,
   and "normalized" keeps the measured hue — so identical *d*, identical LOFO. Combined with rows 3/5 sharing
   the perceived hue, **the five chips carry TWO independent numbers**: absorbed hue and perceived hue. They are
   five *views*, not five pieces of evidence, and should not be read as corroborating one another.
3. **Absorbed hue's brown range is NESTED inside green's** (256.4–259.3 within 255.8–263.1) — no threshold can
   separate nested ranges, so this is not a tuning or S/L-choice problem.

**Likely cause, and it is not a defect in this design:** at 6 drops in 18 ml both oils are pale, and the
chromaticity of a ~1:3000 dilution retains little of the difference that is obvious in the bottle. A band
*ratio* survives dilution because it measures spectral SHAPE; hue is what remains of an almost-white sample.
This predicts colour would discriminate better **undiluted** — precisely where absorbance saturates and the
ratio stops working. **The two approaches want opposite concentrations**, which is a genuine open question for
§6 rather than something to tune here.

Nothing in §1's design changes on this evidence — the chips remain the right *visual* answer to §0's physics.
What changes is the claim attached to them: they illustrate, they do not decide.

### 1a. colorIntrinsicPerceived = the intuitive intrinsic chip (rendered FIRST, Edwin)

The dilution-invariant `colorAbsorbed` reads **blue-violet** (the colour of what's *absorbed*, ≈ complement of the
transmitted green). `colorIntrinsicPerceived` maps it back into the **green-yellow-brown perceived family** by the
**hue complement** — a stable, unique, parameter-free transform:

```
hue' = (hueAbsorbed + 180) mod 360      # keep S = 0.80, L = 0.50
```

It's **stable** (deterministic), **unique** (a bijection on hue — reversible), and inherits the **dilution-invariance**
of `colorAbsorbed` (it's a fixed transform of an invariant colour). It reads green/yellow/brown, so a layperson can
judge it — **this is option (B)'s intuitive-green benefit WITHOUT (B)'s made-up `A_std` parameter** (absorbed ≈
complement of transmitted is a physical fact, not a chosen constant). It is a **canonical, dilution-invariant
"perceived-family" colour** — close to but NOT equal to `colorPerceived` (which is the real, dilution-*dependent* look),
so it must be labelled distinctly. `hue+180°` in HSL is the *simple* complement; a perceptually-exact complement (§6) is
a future upgrade. Rendered **first** so the human-readable intrinsic colour leads the group.

> **UPDATE 2026-07-22 — the `+180°` flip is RETIRED (SPEC_capability_proof.md §8.4, option (b)).** An empirical
> comparison on all 16 K/L/M/N runs showed `+180° HSL` misses the *actual* perceived hue by ~34° (and a Lab-180
> flip is even worse, ~38°). `colorIntrinsicPerceived` now uses the **colorimetric complement** —
> `EvaluationColorUtil.complementViaWhitePoint()` reflects the absorbed chromaticity through the D65 white point
> (`2·white − absorbed`, the mixing-to-white opposite), landing ~4° from the truth. Everything below about
> dilution-invariance and the achromatic guard still holds (it's still a deterministic transform of the invariant
> absorbed chromaticity); only the *transform* changed from a hue rotation to a white-point reflection.

### 1b. colorAbsorbed = option (A), locked

`colorAbsorbed` is the **literal CIE colour of the absorbance** (parameter-free; scale-invariance is automatic).
Consequence Edwin accepted: it reads in the **blue/violet family** (the colour of what the oil *absorbs*, ≈ complement
of the transmitted green) — a **reliable** discriminator (greener vs browner oil ⇒ different colorAbsorbed hue), just
not literally "green". The layperson gap is closed later by a **calibrated verdict word** (§6), not by changing the
colour. Rejected alternative **(B)** — concentration-normalised *perceived* colour (stays green) — needs a made-up
standard `A_std` that biases the chip; recorded, not chosen.

---

## 2. How colour is computed today (reference — unchanged)

> ⛔ **The three defects in this pipeline are named at §7.3** (line-by-line), with the fix at §7.5.

`spectracsPy-core/.../spectrumToColor/SpectrumToColorLogicModule.py`:

```
{nm:value} → SpectralDistribution → sd_to_XYZ(CIE-1931 2°, D65, Integration)
           → XYZ_to_xy            (luminance dropped here)
           → rgbxy.Converter.xy_to_rgb(x,y)  → clamp [0,1]
           → colorsys.rgb_to_hls  → hue°, saturation%, lightness%
swatch = hls_to_rgb(hue, LIGHTNESS=0.20, saturation)   # today: L pinned to 0.20, S measured
```

Plugins reach it only through the Qt-free `EvaluationColorUtil.spectrumToRgbAndHue(spectrum)` → `(rgb, hue°)`. App and
PDF both render the resulting view-models through the **same** `WorkflowItemVisitor` (`QtWorkflowRenderer` /
`MatplotlibWorkflowRenderer`), so **the report colour equals the app colour by construction** (verified in the map;
this is the answer to "check the printed colour matches the app").

---

## 3. Rubber-duck findings (code-grounded, 2026-07-19)

- **F1 — the colour util is too narrow.** `spectrumToRgbAndHue` returns a **lightness-pinned (0.20)** swatch + hue only.
  Grow `EvaluationColorUtil`: `spectrumToHsl(spectrum, converter) -> (h, s, l)` (the measured chromaticity HSL) + a pure
  `rgbFromHsl(h, s, l) -> (r,g,b)`. The plugin then builds each chip: natural `rgbFromHsl(h,s,l)`, normalized
  `rgbFromHsl(h, 0.80, 0.50)`, and **intrinsic-perceived** `rgbFromHsl((h+180)%360, 0.80, 0.50)` (the §1a complement — a
  one-line hue rotate, no new helper needed). Core change, small; the existing `spectrumToRgbAndHue` stays for the
  pumpkin verdict.
- **F2 — the absorbance chips reuse `absorption`.** The DEV plugin already has the `absorption` spectrum (PROCESSING) —
  the three absorbance chips (`colorIntrinsicPerceived`, `colorAbsorbedNormalized`, `colorAbsorbed`) feed it to the util;
  the two perceived chips feed `transmission`. Guard: `absorption` must be finite (no `−log(0)` inf/NaN) before the CIE
  step; confirm `align()` zero-fills outside the 450–620 window (same as perceived does today).
- **F3 — `MetricFieldView` must carry swatch AND value together (the real UI change).** Today the value cell is *either*
  a swatch *or* a read-only `QLineEdit`. Add a `value` alongside `color`; `QtWorkflowRenderer.visitMetricField` lays
  **swatch + read-only field side-by-side**; `MatplotlibWorkflowRenderer.visitMetricField` draws **Rectangle + text**.
  Shared visitor ⇒ PDF gets it free and stays identical to the app.
- **F4 — one "color" row becomes five.** Replace the single `MetricFieldView("color", …)` with the five rows in the
  §1 order (a `LabelView("Colour")` header, then the five).
- **F5/F6 — the lightness nuance.** The pipeline is chromaticity-only (`XYZ_to_xy` drops luminance), so (i) the three
  absorbance chips are **fully** dilution-invariant and the two perceived chips shift via `T^k`; (ii) the "natural L" is
  the converter's lightness for that chromaticity, **not** sample brightness (that is *why* today's code pins 0.20).
  Note this in the HSL field's tooltip; the fixed-L=0.50 chips are the ones to read.
- **F7 — the converter is split by SOURCE (DECIDED, Edwin 2026-07-19: cleaner path for absorbance).** `rgbxy` targets the
  **Philips-Hue gamut** and **clamps** chromaticities outside its triangle — fine for the mild perceived chromaticities,
  bad for an extreme **absorbance** one. So **two chromaticity→RGB backends, keyed on the source spectrum**:
  - **transmission-derived** (`colorPerceived`, `colorPerceivedNormalized`) → keep **`rgbxy`** (so the pumpkin
    hue-verdict thresholds — hue<47 / >66 — stay untouched);
  - **absorbance-derived** (`colorAbsorbed`, `colorAbsorbedNormalized`, `colorIntrinsicPerceived`) → **`colour.XYZ_to_sRGB`**
    (already imported), full-gamut, no Hue clamping.
  Keep dilution-invariance on the absorbance path by working through **chromaticity**: `xy = XYZ_to_xy(sd_to_XYZ(A))`
  (drops luminance ⇒ invariant), reconstruct at a fixed luminance `xyY_to_XYZ(x, y, Y=1.0)`, then `XYZ_to_sRGB` → clamp
  [0,1]. So `spectrumToHsl(spectrum, converter)` takes `converter ∈ {"rgbxy","srgb"}`.
- **F8 — the property test proves the physics.** `hue(CIE(A)) == hue(CIE(2·A))` (absorbance-colour hue invariant under
  scaling) **and** `hue(CIE(T)) != hue(CIE(T²))` (transmission-colour hue shifts). `colorIntrinsicPerceived` inherits the
  invariance (it's `colorAbsorbed`'s hue + a constant 180°). Regression-guards the feature and documents dichromatism.

### 3b. Final-pass findings (2026-07-19)

- **F9 — 🔴 clamp the absorbance before CIE.** `A = −log₁₀(T)` goes **negative** wherever `T>1` (noise / where sample
  reads brighter than reference). Negative "spectrum" values make `sd_to_XYZ` integrate **negative contributions** →
  garbage XYZ / invalid chromaticity. So clamp `A → max(A, 0)` (and a sane ceiling, e.g. 3) before feeding the colour
  util. The peak-ratio maths doesn't need this, but the colour does. (Perceived is already ≥0 by construction.)
- **F10 — 🟠 guard an achromatic source.** A flat/near-grey absorbance (or transmission) has an **ill-defined hue** (the
  chromaticity sits near white, S≈0). Forcing S=0.80 on it would paint a **confident but meaningless** vivid chip. Rule:
  if the source **saturation < a threshold** (e.g. 8–10%), render that chip **grey** and show "achromatic / undefined" in
  the HSL field — never a fake green. This also protects `colorIntrinsicPerceived` (a +180° of a noise hue is still
  noise).
- **F11 — sRGB path details.** On the absorbance path: `xy` (invariant) → `xyY_to_XYZ(x, y, Y=0.5)` (a MID luminance —
  Y=1.0 pushes saturated colours out of gamut) → `XYZ_to_sRGB` (applies the sRGB OETF → gamma-encoded display RGB, same
  kind of value `rgbxy` returns) → **clamp [0,1]** → ×255. Hue/saturation come from the chromaticity, so the Y choice
  only nudges the *natural* chip's lightness (already acknowledged as not-sample-brightness).
- **F12 — MetricFieldView must stay backward-compatible.** After adding `value` beside `color`, the renderers keep
  **three** cases: `color+value` → swatch+field (new); `color` only → swatch (today's dev colour row shape); `value`
  only → read-only field (every existing metric + the ratio rows). Don't collapse to two.
- **F13 — degrade, don't crash.** If `transmission` or `absorption` is missing/`None`, **skip** its chips (or grey them)
  — mirror the existing `if transmission is not None` guard; never let a missing role throw in `evaluation()`.
- **F14 — vertical growth (minor).** Five colour rows + the ratio rows lengthen the metric grid; sanity-check it on the
  `--phone` width (a swatch + HSL field must still fit the 70% value column). Cosmetic, but check.

---

## 4. Implementation phases

```
 Ph │ change                                                            │ where
 ───┼────────────────────────────────────────────────────────────────────┼──────────────────────────────
 K1 │ EvaluationColorUtil: spectrumToHsl(spectrum, converter) +          │ plugin_sdk/util (core) +
    │ rgbFromHsl(h,s,l) [+ (h+180) for intrinsic-perceived]; absorbance   │ SpectrumToColorLogicModule
    │ via colour.XYZ_to_sRGB, transmission via rgbxy                      │
 K2 │ MetricFieldView carries color+value; Qt + matplotlib draw both      │ core view-model + both renderers
 K3 │ DEV plugin emits the 5 chips (order §1) + full-HSL strings          │ spectracs-plugins/…/DevSpectralPlugin
 K4 │ tests: F8 dilution-invariance + srgb-vs-rgbxy + render headless     │ tests
 K5 │ rig (Edwin): five chips + HSL render; app↔PDF colour match          │ rig
 ───┴────────────────────────────────────────────────────────────────────┴──────────────────────────────
 K1→K2→K3 in order (K3 needs both); K4 alongside K1/K3; K5 last. F7 converter split is now by design, not a fallback.
```

> **AS BUILT — K1·K2·K3·K4 IMPLEMENTED + K5 rig-confirmed 2026-07-19 (Edwin: "works so far" on the built-in DEV plugin).**
> - **K1** — `EvaluationColorUtil.spectrumToHsl(spectrum, converter, ceiling)` (rgbxy for transmission, `XYZ_to_sRGB`
>   for absorbance via `xy→xyY(Y=0.5)→sRGB`), `rgbFromHsl`, `chroma(s,l)`; F9 clamp (non-finite/negatives→0, ceiling),
>   empty→(0,0,0). The pumpkin verdict's `spectrumToRgbAndHue` left untouched.
> - **K2** — `MetricFieldView` already held both `color` and `value`; both renderers now draw **swatch + read-only
>   field / Rectangle + text** when both are set (F12 keeps color-only and value-only cases). Shared visitor ⇒ PDF == app.
> - **K3** — DEV plugin emits the five chips in order (`__colourChips`/`__chip`), F13 skip-if-missing, F10 achromatic
>   guard via **chroma** (not raw HLS saturation — near-white reads S≈100% but chroma≈4%).
> - **K4** — `tests/test_color_retrieval.py` (8): F8 invariance (`hue(CIE(A))==hue(CIE(2A))`, `hue(CIE(T))!=hue(CIE(T²))`),
>   negative-A, achromatic, rgbFromHsl, + Qt & matplotlib swatch+HSL render smokes. Registry + pumpkin-wizard-offscreen
>   green (18 total). **Live smoke:** on a pumpkin-ish A, `colorAbsorbed` = blue (H≈219°) and `colorIntrinsicPerceived`
>   = amber (H≈39°, the +180° complement) — the design confirmed.
> - **Note:** `test_workflow_wizard_persistence_offscreen` **hangs pre-existingly** (a modal `QMessageBox` offscreen) —
>   verified by stashing this change; unrelated to colour work.
> - **K5 rig (Edwin) — ✅ works so far** (built-in DEV plugin, real oil): the five chips + HSL fields render. Still
>   worth an eyeball on the generated **PDF** (== app) and the **`--phone`** width when convenient.

## 5. Verification

- **Unit (K4):** the F8 invariance property; five chips are produced from a transmission + its absorbance; the
  fixed-S/L chips have S≈0.80/L≈0.50; `colorIntrinsicPerceived` hue == `colorAbsorbedNormalized` hue + 180°; the HSL
  strings format as `H nnn° · S nn% · L nn%`.
- **Rig (K5):** open the bench on a real oil → five chips render with HSL fields to the right; **colorAbsorbed is not a
  clamped/degenerate colour** and **colorIntrinsicPerceived reads green/yellow/brown**; generate the PDF and confirm each
  chip + HSL matches the app (shared-visitor guarantee, but eyeball it once).

## 6. Out of scope / future

> ⚠ **§7.4 softens the "two approaches want opposite concentrations" tension below** — path length, not dilution,
> is the free variable. **§7.9 adds two items** to this list.

- **Perceptually-exact complement for `colorIntrinsicPerceived`** — §1a uses the *simple* `hue + 180°` in HSL. The
  perceptually-correct complement flips in a **perceptual/opponent colour space** (CIELAB / CIECAM opponent axes — the
  "bent" chromaticity diagrams), not raw HSL hue, so the mapped colour matches the true perceived family more faithfully.
  `hue+180°` is stable and adequate for a bench chip; upgrade to a Lab/opponent complement if the mapped hue feels off
  on the rig. (Edwin future request 2026-07-19.)
- **Calibrated intrinsic-colour verdict** — map the `colorAbsorbed` (or `colorIntrinsicPerceived`) hue to a word
  ("fresh-green / browning / browned") via thresholds, like the pumpkin roast verdict maps hue today. Needs good-vs-bad
  **reference oils** to set thresholds. Separate task, needs data.
- **Pumpkin plugin adoption** — the pumpkin plugin could show the same five chips + a colorAbsorbed verdict; deferred
  until the DEV-bench version is validated.
- Not touched: the wavelength calibration, the peak-ratio metrics (Greenness G / Browning ratio stay the
  dilution-invariant *numeric* discriminators alongside these colour chips).

---

## ⛔⛔ 7. THE PIPELINE DISCARDS THE DIFFERENCE — measured 2026-08-23, DESIGN only

> **Status: DESIGN. Nothing in §7 is built.** §1–§5 remain as-built. This section names the *cause* of §1c's
> "every channel overlaps", prices it, and specifies the fix — and then says plainly what the fix does **not** buy.

### 7.1 The observation that forced it

Edwin looked at two 4 ml aliquots against a phone light table, through ~3 cm of liquid, and saw an
**obvious** difference: Billa Clever visibly browner than Lugitsch. First time it had ever been visible by
eye. Both reports print:

| report row | Lugitsch 2 cap | Billa Clever 2 cap |
|---|---|---|
| `Perceived` | **H 71° · S 100% · L 82%** | **H 71° · S 100% · L 82%** |
| `Perceived · hue-norm` | rgb [108, 120, 54] | rgb [108, 120, 54] |

⛔ **Identical to every printed digit, and byte-identical in the rendered swatch.** The two oils an untrained
observer separates across a room come out as the same colour.

`Intrinsic` fares no better: Lugitsch reads `H 300° · S 100% · L 50%` = rgb **[255, 0, 255]** — pure magenta,
the gamut boundary. ⚠ **Saturation reads 100 % on every row of every metric of all three runs** — §1c saw this
in 2026-07-27 and attributed it to F10 (achromatic guard). That attribution is wrong: it is not an achromatic
source, it is the converter clamping.

### 7.2 ⭐ What is actually in the spectra

Same three runs, computed with CIE 1931 2°/D65 keeping luminance, `XYZ → Lab / sRGB`:

| | 1 cm (cuvette) | | | 3 cm (the eprouvette) | | |
|---|---|---|---|---|---|---|
| | hex | H·S·L | | hex | H·S·L | L\* / C\* / h_ab |
| Lugitsch 2 cap | `#e6fc9b` | 74° · 94% · 80% | | `#c9ed73` | **78° · 77% · 69%** | 89.1 / 62.1 / 118.4° |
| Lugitsch 3 cap | `#c6db8d` | 76° · 52% · 71% | | `#929c6b` | 72° · 20% · 52% | 62.8 / 27.5 / 116.6° |
| Billa 2 cap | `#d1d58f` | 63° · 45% · 70% | | `#a28d62` | **40° · 26% · 51%** | 59.8 / 26.1 / 86.4° |

`ΔE00` at 3 cm: **Lugitsch 2cap ↔ Billa 2cap = 28.8**. (1 cm: 9.5.) A `ΔE00` of 1 is a just-noticeable
difference; 28.8 is "plainly different colours", which is what Edwin saw.

Decomposed at equal `A_Soret`, 1 cm: **ΔL\* −9.7 · ΔC\* −16.0 · Δh only −6.4°** — the difference is ~62 %
chroma and ~38 % lightness, and **only a sliver of hue.**

⇒ **The pipeline keeps the 6° that does not matter and discards the 26 units that do.**

### 7.3 ⛔ The three mechanisms, code-grounded

`spectracsPy-core/.../spectrumToColor/SpectrumToColorLogicModule.py`:

| line | call | what it costs |
|---|---|---|
| **44** | `xy = XYZ_to_xy(xyz)` | **drops Y.** Lightness is gone before anything else runs. Brown *is* dark — that is the ΔL\* −9.7 |
| **47** | `rgb = converter.xy_to_rgb(xy[0], xy[1])` | `rgbxy` signature is `xy_to_rgb(self, x, y, bri=1)` — **brightness pinned to maximum**, and the Philips-Hue gamut mapper pushes to the triangle boundary. That is the ΔC\* −16.0, and the reason **S ≡ 100 %** |
| **56–57** | `measuredLightness`, `measuredSaturation` read back from that RGB | ⛔ **both are functions of chromaticity alone.** A field labelled *lightness* that cannot vary with the sample's lightness is a defect, not a design choice |
| **60** | `hls_to_rgb(hue, lightness, hls[2])` | pinning L for the swatch is **deliberate and fine** — that is hue-normalisation (§1a) |

⚠ **F11 already knew half of this** — *"the Y choice only nudges the natural chip's lightness (already
acknowledged as not-sample-brightness)"*. What F11 did not follow through is that **lightness and chroma are
where the whole signal lives on this oil pair**, so dropping them is not a cosmetic simplification.

### 7.4 ⭐ What this corrects in §1c

§1c (2026-07-27) measured "every channel overlaps", best \|d\| = 0.84, and hypothesised the cause: *"at 6 drops
in 18 ml both oils are pale, and the chromaticity of a ~1:3000 dilution retains little of the difference that is
obvious in the bottle."*

- ⛔ **The hypothesis is refuted.** The difference is present in the spectra at ΔE00 28.8. It is not lost to
  dilution; it is **discarded by the converter**. §1c was measuring the pipeline, not the physics.
- ⭐ **§1c's prediction was right for the wrong reason.** It predicted colour would discriminate better
  undiluted. It does — but via **path length**, not concentration: ΔE00 runs 9.5 → 16.1 → 24.3 → 45.0 at
  1× / 2× / 3× / 5× path. The "two approaches want opposite concentrations" tension in §6 is therefore **softer
  than stated**: render the chip at a longer *nominal viewing path* and keep the measurement dilution unchanged.
- ⭐ **Point 3 of §1c stands and is now explained.** Absorbed hue's brown range nested inside green's is exactly
  what you get when hue is the one coordinate that barely differs.

### 7.5 The fix

> ⛔ **F15 and F16 below are REFUTED by the duck at §7.10 (F21, F22).** They are kept as the reasoning that
> got to §7.11, which is the proposal to build. Read §7.10 before acting on anything here.

- **F15 — keep the luminance.** Replace lines 44–47 with `XYZ → XYZ_to_Lab(XYZ, whitepoint)` for the reported
  numbers and `XYZ_to_sRGB(XYZ, whitepoint)` for the swatch. **Report `L*`, `C*`, `h_ab`** — Lab polar
  coordinates — instead of HSL-of-a-gamut-mapped-RGB. HSL may be kept as a *display* convenience derived from the
  correct sRGB, never as the measurement.
- **F16 — retire `rgbxy` from the measurement path.** It is a Philips-Hue lamp gamut mapper, not a colorimetric
  transform. F7 already split absorbance onto the sRGB path for exactly this reason; **the transmission path needs
  the same treatment.** Keep `rgbxy` only if some renderer genuinely needs a Hue-lamp value, and never read
  H/S/L back out of it.
- **F17 — declare a viewing path.** Colour depends on layer thickness. Render chips at a **declared nominal
  viewing path** (`A × k`, `k` a plugin constant; `k = 3` matches a 4 ml eprouvette seen end-on) rather than at
  whatever the cuvette happens to be, so the chip shows what a person holding the tube would see. Print the path
  next to the chip.
- **F18 — report ΔE00 *between* samples.** A single chip is a visual aid; a **pairwise `ΔE00`** against a
  reference fill is a number. This is the only form in which colour can enter a verdict.
- ⚠ **F19 — S ≡ 100 % must disappear as a side effect.** If it does not, F16 was not applied. Use it as the
  acceptance check.
- ⚠ **F20 — the red tail is fabricated.** Line 41's `align(cmfs.shape)` extends the measured 420–636 nm range to
  380–780 by **holding the last sample**, i.e. one point where the reference is ~33 DN, stretched across ~40 % of
  the visible red. At 5× path that choice alone moves ΔE00 from 45.0 to 38.5. Until the red extension exists,
  **document the extrapolation next to every chip**; afterwards, re-measure §7.2. Chlorophyll's Qy at 660–670 nm
  is entirely outside the range — see [`SPEC_metric_research.md`](SPEC_metric_research.md) §12.

### 7.6 ⚠⚠ WHAT THE FIX DOES NOT BUY — and this is the important part

**The fix restores fidelity. It does not create a discriminator.** Do not let §7.2's 28.8 be read as one.

The three sunflower runs of 2026-08-22/23 include a deliberate loading change (Lugitsch at 2 and 3 capillaries,
`2.21×` actual). Measured against a **neutral floor** `F` = mean absorbance over pigment-free windows
(472–500, 505–555, 588–604 nm):

| | pigment Soret | floor `F` | 3 cm colour | `Q%` |
|---|---|---|---|---|
| Lugitsch 2 cap | 0.565 | **0.031** | `#c9ed73` | 16.21 |
| Lugitsch 3 cap | 1.247 | **0.158** | `#929c6b` | 16.66 |
| Billa 2 cap | 0.617 | **0.181** | `#a28d62` | 21.44 |

⛔⛔ **Overloading the GREEN oil turns it the colour of the BROWN one** — ΔE00 22.2 from its own 2 cap fill, and
only 12.1 from Billa. Meanwhile `Q%` moves **+0.45 (0.9 σ)** across the same 2.2× loading change.

⇒ **The eye separates by floor; `Q%` separates by oil.** Colour, as a channel, is currently a **turbidity meter**.

Three supporting measurements:

1. **The floor drives the colour.** Within-oil pairs across the archive: `corr(ΔE00, |ΔA_valley|)` = **0.926**.
   Pairs matched in turbidity: median ΔE00 **2.57**; mismatched: **8.07**; between-oil: 9.43.
2. **Removing the floor does not rescue it.** Every archived run floor-removed and equalised on the *pigment*
   Soret, IPA only: within-oil median ΔE00 falls 4.53 → **0.90** (a 5× noise win) but between-oil falls
   9.43 → **2.70** — because most of the apparent signal *was* floor. S/N 2.08× → 3.00×, **still overlapping**.
   `Q%` on the same runs: **d = 9.27, clean.**
3. ⛔ **Hue is not floor-immune either.** The algebra suggests it should be (a flat `A` offset scales X, Y, Z by
   one factor, so `a*` and `b*` scale together). It holds only inside Lab's cube-root regime. Adding a synthetic
   flat floor to Lugitsch 2 cap rotates `h_ab`:

   | added flat A | 0.00 | 0.10 | 0.15 | 0.20 | 0.30 |
   |---|---|---|---|---|---|
   | h_ab @ 3 cm | 118.4° | 107.6° | 98.3° | **85.5°** | **54.1°** |

   Rotation over 0→0.20 A: **−3.6° at 0.5 cm, −6.8° at 1 cm, −32.9° at 3 cm.** Across the archive, hue overlaps at
   every path (0.5 cm *d* = 1.29 · 1 cm 1.20 · 3 cm 0.99; Billa's 3 cm hue scatters ±36.9°). ⚠ The 1.8° agreement
   between the two Lugitsch fills in §7.2 is a **cancellation** — 2.2× more pigment pushing hue up against a
   +0.127 floor pushing it down — not a principle.

⭐ **Structurally, colour cannot win this task.** It is a 3-number summary of a ~1500-point spectrum, integrated
against three broad CMFs. The discrimination lives in two narrow bands (568 and 624 nm) spanning ~25 nm. A band
ratio reads them directly; colour averages them away. Floor-removed colour is reading **the same two bands as
`R`/`dQ100`, through a lossy compression** — see [`SPEC_metric_research.md`](SPEC_metric_research.md) §12/§13.5.

### 7.7 ⭐ What colour IS for — and it earned its keep on 2026-08-22

§1c's verdict ("they illustrate, they do not decide") is **upheld and strengthened**. But the evening showed a
third role the spec did not claim:

- ⭐⭐ **An un-fitted, independent check.** `Q%`'s `T = 18.6`, `dQ100`'s `T = 30.0`, `R`'s cut — every one is a
  constant fitted on the corpus it is scored on, which is precisely M9's pre-registration worry. A naked-eye
  difference depends on **no window, no threshold, no corpus**. It is the only channel in the project that cannot
  be accused of circularity.
- ⭐ **A detector, not a meter.** The eye found the neutral floor — a 0.15 A term that none of the shipped metrics
  was flagging, that turned out to be flat, supra-linear in loading (`F ∝ c^2.04` in sunflower vs `c^4.3–6.2` in
  IPA), and immune to 300 s of ultrasound. That finding came from a wall and a phone, not from the rig.
- ⭐ **A validator.** Colour computed only from the spectrum reproduced Edwin's naked-eye judgement, which
  cross-validates the spectra *and* the eye with no calibration constant anywhere.

⇒ **Build F15–F18 for fidelity and for the report, not for the verdict.** The chip should show what a person
holding the tube would see, because that is a claim the instrument can be held to. It should not be scored.

### 7.8 Verification for §7

- **Unit:** a synthetic flat `A` offset of 0.15 must change `L*` and `C*` and must **not** be reported as a
  different *oil*; a 2× absorbance must change `L*`/`C*` while `x,y` chromaticity is unchanged (the F8 property,
  restated in the corrected space); **S must not read 100 % on real data** (F19).
- **Regression against this section:** re-render the three 2026-08-22/23 sunflower runs; at 3 cm the hexes must be
  `#c9ed73` / `#929c6b` / `#a28d62` and pairwise ΔE00 22.2 / 12.1 / 28.8.
- **Rig:** hold the eprouvette against a white wall next to the rendered chip at the declared viewing path. If they
  disagree, F15–F17 are not correctly applied.
- ⚠ **Do not add a colour threshold to any verdict on the strength of §7.2.** §7.6 is the reason.

### 7.9 Open, for §6

- **A floor-immune colour coordinate.** None of `L*`, `C*`, `h_ab` is one. If the floor is killed at source (a
  triglyceride solvent — see [`SPEC_metric_research.md`](SPEC_metric_research.md)), the question becomes moot for
  the reported chip but stays open for any archive comparison across fills.
- **Re-measure §7.2 after the red extension.** 49 % of the *pigment* colour difference (floor-matched, attributed
  per wavelength — XYZ is linear in transmittance, so the decomposition is exact) sits in **623–636 nm**, 12 nm
  from the clamp, with a further unmeasured share at Qy 660–670. Colour is the only channel that would gain
  directly from the extension **and** the only one currently integrating over a window (500–560) that contains
  nothing but floor.

### ⛔⛔ 7.10 Rubber duck on F15–F20 (code-grounded, 2026-08-23) — two of them are wrong

> Read against the actual files. **F15 and F16 as written would break working behaviour**; F17–F20 need
> qualifications. The corrected proposal is §7.11.

- **F21 — ⛔⛔ F15 BREAKS §0 AND F8. Dropping Y is the mechanism, not the mistake.** `EvaluationColorUtil.__cieXy`
  says it in its own comment: *"CIE → chromaticity xy (drops luminance ⇒ dilution-invariant)"*. That is what §0
  asks for, and `tests/test_color_retrieval.py:50` locks it — `hueDelta(hue(CIE(A)), hue(CIE(2·A))) < 2.0`.
  **Keeping luminance makes the five chips concentration-dependent and fails that test.**
  ⭐ And the tension is real, not a bug: **brownness IS lightness IS concentration.** §7.6 proved it — loading
  Lugitsch 2.2× harder turns it Billa's colour. You cannot have a dilution-invariant chip that also shows
  "browner". ⇒ **Do not touch the five chips. ADD a sixth.**
- **F22 — ⛔ F16 would silently re-scale the pumpkin verdict.** `spectrumToRgbAndHue`'s docstring:
  *"UNCHANGED; the pumpkin roast verdict depends on its hue output, so its converter must stay `rgbxy`"* — and the
  Roast Ampel's thresholds (4.4; band 6.0→3.0, recalibrated 2026-07-25) are fitted on **that** hue.
  ⇒ `rgbxy` stays on the verdict path. F7's source-keyed split already exists; **extend it, don't replace it.**
- **F23 — ⭐ §7.3's diagnosis is incomplete: there are TWO `S ≡ 100 %` mechanisms, one per path.**

  | path | converter | why S pins to 100 % |
  |---|---|---|
  | transmission (`Perceived`) | `rgbxy` | `xy_to_rgb(x, y, bri=1)` — brightness pinned, Hue triangle clamps |
  | absorbance (`Intrinsic`) | `XYZ_to_sRGB` | `__hslFromXy` rebuilds at **fixed Y = 0.5**, then **clamps [0,1]** — a saturated chromaticity at Y = 0.5 is out of sRGB and clips to the boundary → rgb [255, 0, 255] |

  ⇒ **F16 alone would not fix the `Intrinsic` chips** — F7 already moved them to sRGB and they *still* read 100 %.
  Their cure is **gamut mapping** (desaturate toward white until in gamut) or a lower reconstruction Y, not a
  converter swap.
- **F24 — ⚠ F17's path multiplier collides with two existing guards.** (a) `__resolveCeiling(RELATIVE)` scales with
  the spectrum so `k·A` is safe — but `test_color_retrieval` passes an **absolute 3.0**, and any plugin still doing
  so would clip everything at `k = 3`. (b) The perceived chip is built from **transmission**, so scaling path means
  `T → A → k·A → T`: `T = 0` is a log-domain error and `T > 1` gives `A < 0`, which `__sanitize` **silently clamps
  to 0**. ⇒ F17 must operate on absorbance, guard `T ∈ (0, 1]`, and require `RELATIVE`.
- **F25 — ⚠ the achromatic guard needs re-deriving once S is real.** `ACHROMATIC_CHROMA = 8.0` against
  `chroma = (1 − |2L−1|)·S`. Today `S ≡ 100`, so chroma is driven by L alone. With a real S, chroma collapses and
  the guard may fire on **genuine** samples. `test_color_retrieval.py:88/113` assert that grey sources fall *below*
  the threshold; **nothing asserts real samples stay above it.** ⇒ add that assertion, then re-derive on the archive.
- **F26 — ⚠ three callers, not one.** `SpectralColorUtil.spectrumToColor` (façade, line 228),
  `SpectrumSynthesisUtil` (line 120 — **virtual-device synthesis**), and `EvaluationColorUtil` (×2). Touching
  `SpectrumToColorLogicModule` changes synthetic spectra too, i.e. the virtual device's own colours.
- **F27 — ⛔ M3 sealing makes "change" and "add" very different risks.** `__resolveCeiling`'s comment already sets
  the precedent: *"plugins ship as sealed versioned DB blobs (M3): a linearized host running an older assigned
  plugin version would clamp real signal with nothing to warn about it."* Same hazard here — a host that changes
  what `spectrumToHsl` returns silently alters every sealed plugin's chips. **Adding a method is safe; changing an
  existing one's output is not.** This is the strongest independent argument for F21's "add a sixth chip".
- **F28 — ⚠ F18 has an unmet dependency.** `ΔE00` *between* samples needs a reference fill, and a workflow holds
  **one** sample. It needs the stored reference from [`SPEC_history_tracker.md`](SPEC_history_tracker.md) or the
  saved-runs store. ⇒ sequence it after, or scope it to "ΔE00 against the run selected in the saved-runs list".
- **F29 — ⚠ F20's `align` is shared by every path and every OS.** The fabricated red tail lives in `__cieXy`'s
  `align(cmfs.shape)`, which both converters and all three callers go through. And
  `SpectrumToColorLogicModule:36-40` records that the **on-device build raises** on a grid mismatch where desktop
  tolerates it. ⇒ any change to grid/extrapolation handling is a two-OS change, not a one-liner.
- **F30 — ⭐ a floor-correction feature would be silently destroyed by `__sanitize`.** It clamps negatives to 0
  (F9), and floor-corrected absorbance **is** negative across the valley (measured −0.015 / −0.013 on the two
  sunflower fills). If §7.9's floor question ever becomes a feature, `__sanitize` needs a sign-preserving mode.

### ⭐ 7.11 The corrected proposal — one new chip, two real defects fixed

**Supersedes F15/F16.** Three separate pieces of work, deliberately separable:

1. **ADD `colorAsSeen` (chip 6)** — luminance kept, rendered at a **declared viewing path**, proper sRGB with gamut
   mapping. This is the only chip that answers "what does the tube look like", and the only one that can be checked
   against a wall. It is **not** dilution-invariant, by design, and must be labelled so.
2. **FIX `S ≡ 100 %` on the existing five** — gamut-map instead of clamp (F23). This is a genuine defect: the
   reported saturation carries no information today. Hue is unaffected, so §0, F8 and the verdict all survive.
3. **DEFER `ΔE00`** until a reference source exists (F28).

⛔ **Not in scope:** anything that changes what the existing five chips report. F27.

### 7.12 Implementation phases

```
 Ph│ change                                                            │ where                         │ gate 
───┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┼──────
 C0│ CHARACTERISATION FIRST — pin today's output on the three          │ tests/                        │ —    
   │ 2026-08-22/23 sunflower runs (5 chips x H,S,L) so any later       │                               │      
   │ change shows up as a diff, not a surprise.        F26/F27         │                               │      
───┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┼──────
 C1│ gamutMap(XYZ) -> in-gamut XYZ: desaturate toward the white        │ plugin_sdk/util/              │ C0   
   │ point until sRGB lands in [0,1]; __hslFromXy uses it instead      │                               │      
   │ of the raw clamp.  => S stops reading 100 %.          F23         │                               │      
 C2│ re-derive ACHROMATIC_CHROMA on the archive, and add the           │ EvaluationColorUtil + tests   │ C1   
   │ MISSING assertion: real samples stay ABOVE the guard.  F25        │                               │      
───┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┼──────
 C3│ spectrumToLab(absorbance, path=k, ceiling=RELATIVE)               │ plugin_sdk/util (new only)    │ C1   
   │   -> (L*, C*, h_ab, rgb).  KEEPS Y.  NEW method, nothing          │                               │      
   │ existing touched.  Guards T in (0,1], requires RELATIVE.          │                               │      
   │                                           F21/F24/F27             │                               │      
 C4│ DEV plugin emits chip 6 `colorAsSeen` + a                         │ spectracs-plugins/DevPlugin   │ C3   
   │ "viewing path k = 3 cm" label.                                    │                               │      
   │ The five existing chips UNTOUCHED.                    F21         │                               │      
 C5│ regression: the three sunflower runs must render                  │ tests/                        │ C4   
   │ #c9ed73 / #929c6b / #a28d62 at 3 cm.                 §7.8         │                               │      
───┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┼──────
 C6│ document the fabricated 636-780 nm tail beside every chip;        │ DevPlugin + spec              │ C4   
   │ two-OS check on align().                          F20/F29         │                               │      
 C7│ rig: hold the eprouvette against a white wall next to chip 6      │ rig (Edwin)                   │ C4   
   │ at the declared path.  Disagreement => C1/C3 wrong.  §7.8         │                               │      
───┴───────────────────────────────────────────────────────────────────┴───────────────────────────────┴──────

 DEFERRED — not sequenced:
    │ Cx  ΔE00 vs a stored reference fill         │ needs SPEC_history_tracker      F28         
    │ Cy  sign-preserving __sanitize              │ only if §7.9 floor becomes real F30         
    │ Cz  retire rgbxy anywhere                   │ ⛔ NOT WHILE THE AMPEL SHIPS    F22          

 C0 first, always.  Then two INDEPENDENT chains:   C1 -> C2      (fixes the five)
                                                   C1 -> C3 -> C4 -> C5   (adds the sixth)
 C6 and C7 follow C4.

 ⚠ C1 changes what the FIVE EXISTING chips report (saturation) — sealed-plugin risk, F27.
   C3/C4 change nothing existing.  If F27 is judged too high, ship C3/C4 ALONE and leave
   S = 100 % documented as a known defect.
```

⚠ **The honest cost/benefit.** C3/C4 buy fidelity — a chip that matches the tube — and are risk-free under F27.
C1/C2 fix a real defect but touch sealed-plugin output for a field (`S`) that **carries no information today and
will carry little after**, since §7.6 shows the whole channel is a turbidity meter. ⇒ **C3/C4 are worth building;
C1/C2 are worth doing only when something else already forces a core colour change.**


### ⭐⭐ 7.13 AS BUILT — 2026-08-23 (579 tests green: 520 app + 59 plugins)

**Two of the planned phases changed on contact with the code. Both changes were forced by measurement.**

| planned | what happened |
|---|---|
| **C1** gamut-map instead of clamp | ⛔ **TRIED AND REVERTED.** Measured: mixing toward white shifts the reported **hue by up to 45°** on the badly out-of-gamut absorbed chromaticities (287.5° → 252.7° on a pumpkin absorbance) — and hue is the one thing the verdict and F8 depend on. Worse, **it does not fix `S ≡ 100 %` anyway**: the gamut boundary is exactly where `min(r,g,b) = 0`, which *is* S = 100. ⇒ `S` pinning is intrinsic to reading HSL saturation off an out-of-gamut chromaticity, whatever the rendering. `gamutMapXy` is kept as an opt-in diagnostic (its `reach` says how unrenderable a chip is) and is **not in any reported-number path**. |
| **C1′** *(what shipped instead)* | ⭐ **`spectrumToPurity`** — **excitation purity**, the distance from D65 white toward the spectrum locus, in percent. Defined on the chromaticity diagram, so no gamut enters. Dilution-invariant, like the chips it sits beside. **Measured on the three sunflower runs: HSL `S` = 100.0 / 100.0 / 100.0 → purity 88.3 / 77.1 / 68.7 %.** |
| **C2** re-derive `ACHROMATIC_CHROMA` | **NOT NEEDED.** The HSL path is byte-for-byte unchanged, so the guard's inputs are unchanged. |
| **C3** `spectrumToLab(absorbance, path)` | ✅ built — and it exposed a **third** trap beyond F29's. Details below. |
| **C4** chip 6 in the DEV plugin | ✅ built as **"As seen · 3 cm"**, plus an **"Intrinsic · purity"** row. |
| **C5** regression on the three runs | ✅ `#caed72` / `#989c6f` / `#a48e5b` at 3 cm. |
| **C6 / C7** | C6 folded into the docstrings + the chip tooltip. C7 (rig) still owed. |

#### ⛔ The third trap — `align` again, twice

`__cieXyzDense` exists because **two** ways of getting a transmittance onto the CMF grid are wrong:

1. **`align`'s constant-hold** (F29) extrapolates the *falling flank of the 624 nm band* flat across 636–780 nm.
   Measured: Billa Clever renders **olive-green `#809341`** where the eye says khaki-**brown** — it **inverts the
   visual ordering of the two oils**. The un-measured red is not a rounding error; it decides the answer.
2. **Sparse `T = 1` anchors + `align`** is worse. Its cubic interpolation **overshoots** across the 1 nm step onto
   an opaque Soret: `Y = 2.61`, `L* = 144`, `#ff00f5`. Nonsense, and silent.

⇒ dense, **linear**, explicit, with un-measured wavelengths transparent. ⚠ Still an assumption, and **wrong at the
blue end** (the Soret core below 420 nm absorbs *more*, not less) — but the CMF weight there is small under linear
interpolation, and it is the conservative choice in the red where the discrimination lives.

#### What actually changed

```
 core   EvaluationColorUtil   + spectrumToPurity(spectrum, ceiling)        -> excitation purity %
                              + spectrumToLab(absorbance, path, ceiling)   -> (L*, C*, h_ab, rgb)  KEEPS Y
                              + gamutMapXy(x, y, luminance)                -> diagnostic only, unused
                              + __cieXyzDense / __lch                      -> internals
                              ~ __cieXy refactored onto __cieXyz           -> behaviour identical
 plugin DevSpectralPlugin     + "As seen · 3 cm" chip  (__VIEWING_PATH_CM = 3.0, declared, not fitted)
                              + "Intrinsic · purity" row
 tests  test_color_retrieval  + 9 (ColourFixTest);  the S=100 defect is now ASSERTED so it cannot be
                                "fixed" by accident without this section being revisited
        test_dev_plugin_…     ~ chip set 10 -> 11
```

⭐ **Nothing existing changed its output.** The five chips, `spectrumToHsl`, `spectrumToRgbAndHue`, the pumpkin
verdict and F8 are all untouched — F21/F22/F27 respected in the end, though for the reasons in this section rather
than the sealing argument that motivated them (nothing is shipped yet, so F27 never actually bit).

⏸ **C7:** first evidence in §7.14 — Billa's hue predicted to 2° off an uncalibrated phone photo, and the
constant-hold red tail refuted out of sample. Still owed in controlled form (grey card, fixed exposure, equal
fill depths).

### ⭐ 7.14 C7 — the rig check, done with a phone  *(2026-08-23; PARTIAL)*

Three eprouvettes, ~3 cm of liquid, end-on against a phone light table. No instrument in the loop.
`spectracs-references/business/internal/pics/2Lugitsch1BillaClever.jpg`. ⭐ The capillaries left standing in
each tube label its loading — **N capillaries show as 2N rings** (doubled by reflection), which is how the
tubes were identified: TOP 4 rings = Lugitsch 2 cap, BOTLEFT 4 = Billa 2 cap, RIGHT 6 = Lugitsch 3 cap.

| tube | hue photographed | hue predicted (chip 6, 3 cm) | Δ |
|---|--:|--:|--:|
| **Billa Clever 2 cap** | **90.1° ± 3.5** | **88.0°** | **+2.1°** |
| Lugitsch 3 cap | 114.6° ± 4.6 | 111.3° | +3.3° |
| Lugitsch 2 cap | 106.2° ± 2.0 | 118.2° | **−12.0°** |

⭐ **Billa to within two degrees, from an uncalibrated phone with automatic white balance.** And the two
2-capillary fills — the standard recipe — separate by **16.1° against a combined scatter of ±4.0°, four sigma,
by eye.**

⭐⭐ **The unlooked-for result: this refutes `align`'s constant-hold red tail out of sample.** §7.13 chose
"transparent above 636 nm" from physics plus one qualitative cue, which was circular. The photograph arrived
afterwards and could have refuted it: **"hold" predicts Billa at 115.1°, "transparent" 86.4°, the photograph
90.1° ± 3.5.** 26° wrong versus 4° right, and the hue *span* 4.5° versus a photographed 27.5°. The un-measured
40 % of the visible red is not a rounding error — it decides the answer, and the conservative pad is the right
one. ⇒ another argument for the red extension.

⚠ **Why this is PARTIAL, not C7 closed:**

1. **Lightness is unusable.** `L*` scatters ±8.5 within the RIGHT tube alone (against ±2.0 for hue) — the tubes
   are unevenly backlit and auto-exposed. ⭐ Edwin's own reading, and it is physically right: a change in
   illumination *intensity* scales X, Y, Z uniformly, moving `L*` and leaving hue alone. **Only hue survives an
   uncalibrated photograph.**
2. **The two Lugitsch fills come out in the wrong ORDER** — photographed 3 cap > 2 cap in hue, predicted the
   reverse. But 8.5° apart against ±5.1° combined scatter is **1.7 σ**, and the prediction's own separation is
   6.9°. ⛔ Not resolved by this photograph.
3. **The 2 cap Lugitsch misses by −12.0° against its own ±2.0 scatter** — the one genuine disagreement. It is
   also the oldest fill in the frame (measured 22:35, photographed 03:24, with 300 s of sonication and desk
   light in between) and browning moves hue exactly that way — but Billa is equally old and did not move, so
   ageing is a hypothesis, not an explanation.
4. **No grey card, no fixed exposure, unequal fill depths.**

⇒ **C7 proper still owed:** equal fill heights, grey card in frame, fixed manual exposure and white balance,
chip 6 rendered beside the tube at the declared path.

---

## ⭐⭐ 7.15 AS BUILT — 2026-08-24: HSL retired from the chips, one CIE path, four chips

**582 tests green (520 app + 62 plugins). `SDK_VERSION` unchanged at 1.** The full reasoning, with the
measurements behind every decision, is `docs/DOC_colour_geometry.md` (22 pp) — this section is the
contract.

### 7.15.1 What forced it

Four archive checks over the **88 labelled isopropanol runs** (`diagnostics/dominant_wavelength_archive.py`,
same corpus and labelling as `SPEC_metric_research.md` §12). Three refuted a claim this spec made:

| claim | result |
|---|---|
| §7.13 C1′ — *"purity discriminates where HSL saturation cannot"* | ⛔ It carries information where `S` does not, but it does **not** separate the oils: *d* = 0.56, ranges overlapping. |
| a proposed replacement — dominant wavelength | ⛔ Undefined on **31 %** of runs (the ray exits the purple line), *d* = −0.08 where defined, and **r = 0.923 with the capture's blue edge**. It reports where the measurement starts. |
| §1a — *"the white-point complement is ~4° from the true perceived hue"* | ✅ **Confirmed and improved: 2.50 ± 1.90° over 88 runs**, against 52.7° for the retired `+180°` flip. Does not degrade where the complement is imaginary. |
| new — is `Absorbed-complement` a real colour? | ⛔ Outside the **spectrum locus** on 10 % of runs, at or past the edge of vision on 25 %. Predictable exactly: absorbed `p_e` above ≈ 76 %. |

⭐ And the reason none of them work, measured: **`theta_W` = 244.06 ± 1.25° over the whole archive.**
The absorbed direction is a constant of the chlorophyll-derivative family. What varies between oils is
the RADIUS — which is precisely what a dilution-invariant chip discards. Not a software problem.

### 7.15.2 The contract

**Core (`EvaluationColorUtil`) — ADDITIVE ONLY.**

```
+ spectrumToChromaticity(spectrum, source=ABSORBANCE|TRANSMITTANCE, ceiling)  -> (x, y) | None
+ complementOf(xy) / directionFromWhite(xy) / purityOf(xy) / lchOf(xy) / isRenderable(xy)
+ ABSORBANCE / TRANSMITTANCE / ACHROMATIC_CHROMA_LAB = 7.0
~ __cieXyz  now delegates to __cieXyzDense (P1/D5) -- CHANGES NUMBERS on every chromaticity chip
= spectrumToHsl / rgbFromHsl / chroma / ACHROMATIC_CHROMA / spectrumToRgbAndHue  ALL KEPT
```

⛔ **Nothing was removed, and that is load-bearing.** Plugins ship as sealed DB blobs against the host's
SDK; `checkSdkCompatibleVersion` is strict equality; three sealed rows exist. Shrinking this surface
would force `SDK_VERSION` to 2 and break all of them. **"Retire HSL" means the dev plugin stops calling
it.**

⛔ **`source` is load-bearing too.** "Un-measured = transparent" is `A = 0` for an absorbance and `T = 1`
for a transmittance. Getting it wrong pads the un-measured red as OPAQUE and swings `theta_W` by ~13°.
It is an explicit argument, never inferred.

**Model.** `MetricFieldViewStyle.isOutOfGamut` — the chromaticity is outside sRGB, so the swatch is a
per-channel clamp and not the colour the numbers describe. Rendered as a dashed amber border by **both**
`QtWorkflowRenderer` and `MatplotlibWorkflowRenderer`. Carried as style, not appended to the value text,
so it survives into the report JSON as a queryable fact.

**Plugin.** Four chips, in this order, plus one demoted row and a sub-tab:

| chip | reports | why |
|---|---|---|
| **`Transmitted from absorbance · ×3 path`** | `L* · C* · h` | ⭐ FIRST. The only chip the archive measured as carrying anything, and the one that matched a photograph to 2.1°. Its `L*` is a measurement and its `C*` (30–63) is inside Lab's domain. |
| `Absorbed` | `theta_W · purity` | |
| `Absorbed-complement` | `theta_W` **only** | its chroma would describe an imaginary stimulus |
| `Transmitted-measured` | `theta_W · purity` | |
| `Absorbed · purity` (row) | `%` | demoted; kept as the free predictor above |
| sub-tab `Colour · processing rungs` | the de-spiked / baseline recomputations | eight chips reporting a near-constant do not belong in the headline |

⛔ **No chip prints `L*` except the first.** At the fixed swatch luminance it is the constant 76.07, and
a constant that looks like a measurement is the defect this section exists to remove.

⭐ **`theta_W`, not `h_ab`, is the reported hue** — measured, not chosen: 2.50° against `h_ab`'s 5.60°
and the retired HSL's 4.15°. Lab's hue depends on chroma by design, and these chips compare colours
whose chroma differ ~4×.

### 7.15.3 What this section VOIDS in §7.13

- ⛔ **C2 ("NOT NEEDED — the HSL path is byte-for-byte unchanged")** is void. The guard was re-derived
  in Lab units: near grey, where it is the only place it fires, HSL chroma and `C*` track at ratio ≈ 0.85,
  so `8.0` ports to `ACHROMATIC_CHROMA_LAB = 7.0`.
- ⛔ **C1′'s discrimination claim** is void — see 7.15.1. Purity stays for the reason C1 gave (it is the
  honest replacement for `S ≡ 100`), not for the reason C1′ gave.
- ⚠ **The `S = 100` tripwire test still passes**, because `spectrumToHsl` was kept. It now guards a
  method the chips no longer call.
- ✅ **§7.14's phone check stands** — the `×3 path` chip is byte-identical across P1, which is the
  check that P1 did only what it claimed.

### 7.15.5 The whole archive regenerated — and one regression it caught

**All 203 archived reports re-rendered onto the new chip set, 0 failures**
(`diagnostics/regenerate_reports.py --write`). The pre-2026-08-24 originals are at
`spectracs-references/tmp/oldPdfs/`, an exact 205-file mirror.

⛔ **`oldPdfs` lives INSIDE the archive root**, which every diagnostic walks — so without an exclusion
each run would be counted TWICE and every archive statistic silently corrupted. `EXCLUDED_DIRS =
{"oldPdfs", "discussion"}` is now honoured by `peak_ratio_archive`, `all_metrics_archive`,
`regenerate_reports`, `report_reconstruct` and `settling_sweep`. ⚠ Earlier backups (`tmp_backup_*`) were
placed OUTSIDE `tmp/` for exactly this reason; anything added under `tmp/` in future must be excluded
here too.

⭐ **The bulk run caught a regression the unit tests did not.** Two runs of the `20260806A` null series
have an absorbance that is negative at *every* wavelength, so it sanitizes to nothing. F10 and F13 are
different cases and the rewrite had collapsed them:

| | before the rewrite | after (wrong) | fixed |
|---|---|---|---|
| spectrum **missing** | no row | no row | no row |
| spectrum **present, no positive signal** | grey `achromatic / undefined` | ⛔ row vanished | grey `achromatic / undefined` |

⇒ A null run looked like a run whose colour had simply not been computed. Fixed, and asserted by
`test_a_spectrum_with_no_positive_signal_still_renders_a_chip`.

⚠ **One deliberate behaviour change beyond the phases.** `__asSeenChip` also returned `None` on such a
sample — pre-existing, and tolerable while that chip sat last. It now leads the list, so a silent gap
reads as "not computed" rather than "there is no colour here". It now renders the same grey
`achromatic / undefined` as every other chip. This is the one place the implementation went past what
§7.15 was asked for; it is here so it is a decision on record rather than a drift.

### 7.15.4 Owed

⏸ Rig click-through · ⏸ the PDF report by eye · ⚠ old saved runs keep their old labels (the label is
data in the `DbMeasurement` blob; no migration) · ⚠ the android `app_src` trees carry stale copies of
`EvaluationColorUtil` and were deliberately not touched · ⛔ the roast verdict's own `align` red tail is
still live, on purpose.

---

## ⭐ 7.16 Why the SOLVENT changes what the EYE can see — physical argument *(2026-08-24; ARGUMENT, not measurement)*

**Edwin's observations, both from the bench.**

1. After many eprouvettes of oil in isopropanol, switching to sunflower oil made the difference between
   the green and the brown oil obvious **by eye, immediately**. He is explicit that it might have been
   accident, and that he cannot be sure he would have noticed it in isopropanol earlier.
2. **The red peak became more pronounced** in sunflower oil — and the same had been seen in the
   **white spirit** session.

⚠ The second is the more diagnostic, and it is what identifies the mechanism: it happened in *both*
solvents. White spirit (n ~ 1.44) and sunflower oil (n = 1.473) share nothing except being **nonpolar
and index-matched to the oil**, so both DISSOLVE it where isopropanol only emulsifies it.
⛔ Do not read this section as "sunflower": the property is *true dissolution*, not that solvent.

⛔ **This section is ARGUMENT. Nothing in it is measured.** It exists because the archive appears to
contradict the observation and does not; §7.16.1 is why. The two experiments in §7.16.5 are what would
settle it, and until they run this is a hypothesis with a mechanism, not a result.

### 7.16.1 ⭐⭐ The instrument cannot see what the eye sees — by construction

`T = S/R`, and `R` is the **solvent blank**. Two consequences, and both are design, not defect:

1. **The solvent's own colour divides out.** Sunflower oil is visibly yellow; the measurement removes it
   exactly. Every colour number in this spec and in `DOC_colour_geometry.md` describes *the pumpkin
   oil's excess over the solvent*. The eye in front of an eprouvette sees **the whole liquid**.
2. **A scattering veil largely divides out too**, because the blank is the same preparation with the
   same turbidity.

⇒ The archive's silence on this is not evidence against the observation. **It is a different quantity.**
§7.16.2 and §7.16.4 are both invisible to `T = S/R` on principle.

### 7.16.2 The dominant mechanism: refractive-index matching

| | n | m = n_oil / n_medium | scattering factor |
|---|--:|--:|--:|
| pumpkin oil | 1.47 | — | — |
| **isopropanol** | 1.377 | 1.0675 | **1.98 × 10⁻³** |
| **sunflower oil** | 1.473 | 0.9980 | **1.85 × 10⁻⁶** |

where the scattering factor is

```math
\Big( \frac{m^{2}-1}{m^{2}+2} \Big)^{2}
```

⇒ **about 1070× less scattering in sunflower oil.** In isopropanol the oil never dissolves — it
emulsifies, and every droplet is a lens. In sunflower oil, like into like: the droplets are optically
invisible even where they are physically present. This is the same `n` argument
`DOC_solvent_and_hue.md` §2 makes from the *baseline* side; here it is made from the *visual* side.

### 7.16.3 ⭐ Why scattering specifically destroys a colour DIFFERENCE

**Scattering puts a floor under the transmittance, and the floor kills the exponential.**

```math
T_{obs}(\lambda) = T_{direct}(\lambda) + S
```

$S$ is forward-scattered light. It took short randomised paths through little absorbing material, so it
is **much whiter than the direct beam**.

In a clear liquid at 3 cm, $T = 10^{-kA}$ ranges over orders of magnitude: the deep bands go genuinely
black and the windows stay bright. That dynamic range **is** the saturation, and it is the whole
mechanism §7 of this spec rests on. With a veil, $T$ can never fall below $S$ — the deep parts of the
spectrum are clamped, the spectrum flattens, and the chromaticity walks toward white.

⇒ Both samples become pale yellow-grey, and pale colours are hard to separate without a side-by-side
reference. **That is a sufficient explanation of observation 1.**

⛔ **It does NOT explain observation 2, and a first draft of this section claimed it did.** The contrast
reduction goes as $T_{base}/(T_{base}+S)$, which bites hardest where $T$ is *lowest* — the Soret at
$T \approx 0.03$, not the red bands at $T \approx 0.6$. The floor predicts scattering flattens the
**blue** and spares the **red**; observation 2 is the reverse. §7.16.4a is the mechanism that predicts
the right asymmetry.

### 7.16.4 The second mechanism, which also favours sunflower

Transmittances multiply: $T_{total} = T_{solvent} \times T_{pumpkin}$.

Sunflower oil is yellow — it absorbs blue. And **blue is where the two pumpkin oils AGREE**: the Soret
dominates both, which is why $\theta_W$ is near-constant across the archive
(`DOC_colour_geometry.md` §3.1). In the red, sunflower is transparent, so the pumpkin difference passes
undiminished.

⇒ The solvent acts as a **filter that suppresses the band where the oils are identical and passes the
band where they differ.** Isopropanol, being colourless, leaves the uninformative blue residue in the
light reaching the eye, diluting the contrast.

### ⛔⛔ 7.16.4a Observation 2 — a mechanism proposed and REFUTED by its own test  *(2026-08-24)*

⚠ **§12.6 of `SPEC_metric_research.md` already established the phenomenon**, on 110 fills and before this
section existed: measured as a height above a local chord on **Soret-normalised** absorbance, the 568 nm
band runs 0.087–0.213 across 106 isopropanol fills and 0.235–0.289 across four white-spirit fills — no
overlap — and it already rules turbidity out ($r$ = −0.016 with normalised turbidity, and the spirit
fills are the *more* turbid). §12.6 records the cause as **unsettled**. This section does not change
that; it removes one candidate.

**What was proposed here, and is now withdrawn.** That a grating maps input angle onto wavelength, so an
emulsion's ~17° forward lobe broadens the effective linewidth: narrow features wash out, broad ones
survive. It has the right shape and it is wrong.

**The test.** ⭐ **Convolution conserves area.** Blurring lowers a band's height and widens it, leaving
the integral alone. So measure the 624 nm band's **area** above its local chord, as a fraction of the
**Soret** area — dose-free, since both scale with concentration
(`diagnostics/band_width_by_solvent.py`):

| | n | A_Soret (the dose check) | 624 area / Soret area |
|---|--:|---|---|
| **index-matched** (white spirit + sunflower) | 7 | 0.877 ± 0.263 | **0.0221 ± 0.0107** — [0.0110, 0.0368] |
| **isopropanol** | 72 | 0.762 ± 0.146 | **0.0013 ± 0.0010** — [0.0001, 0.0036] |

⇒ **16.6× at matched dose** (the two A_Soret populations differ by 1.2× and overlap), $d$ = +6.65, ranges
separate.

⛔ **A 16.6× dose-free AREA difference cannot be convolution.** Resolution loss is refuted by its own
prediction.

⛔ **And so are the other optical candidates, all for one reason: they hurt the SORET more.**

- **veiling glare** scales contrast by $T_{base}/(T_{base}+S)$, which is severe at the Soret
  ($T \approx 0.03$) and mild at 624 nm ($T \approx 0.6$) — that makes the *ratio* larger in
  isopropanol, not 16.6× smaller;
- the **package / sieve effect** flattens the strongest bands most, so it too predicts a larger
  Soret-normalised Q band in the emulsion. §12.6 had already noted it "predicts the opposite sign".

⇒ **What survives is not optics at all.** At essentially the same pigment load the 624 nm transition
carries 16.6× less area relative to the Soret in isopropanol — a change in the pigment's own state
(speciation, or aggregation at the droplet interface), not in how the light gets to the detector.
⏸ Unsettled, exactly as §12.6 left it.

#### ⚠ 7.16.4b What this test could NOT do — the width comparison is invalid

The first cut measured **equivalent width** $W = \text{area}/\text{height}$ and reported the isopropanol
band as 3× *narrower*. ⛔ **That number is confounded and must not be quoted.**

- Within isopropanol, $r(W,\ \text{height})$ = **+0.543**, and $W$ rises monotonically across height
  tertiles: 1.63 → 2.21 → 2.70 nm. A band near the noise floor has its "peak" set by a noise excursion,
  which inflates the height and deflates $W$.
- **The height populations do not overlap at all** — every isopropanol band (0.0041–0.0256 A) is fainter
  than the weakest index-matched one (0.0371 A). There is no fair slice on which to compare $W$.

⚠ **And the diffuser A/B could not validate $W$ either.** It is the archive's one known blurring event,
so it should have shown $W$ rising — but the diffuser erases the 624 band completely (no band above the
chord on all five diffuser-IN runs), so $W$ is undefined there. **$W$ has never been demonstrated to
detect blurring on this instrument.** The conclusion above rests on AREA alone, which needs no such
demonstration.

### 7.16.5 ⚠ Where to hold back, and the experiments

⚠ **All three arguments push the same way, which means none of them is being tested by the
observation.** And Edwin's own caveat is the right one: a side-by-side pair in one light is far more
sensitive than sequential viewing on different days. The eye adapts and memory for colour is poor, so
*"I would have noticed it in isopropanol"* is not safe.

**E1 — the premise, ten seconds.** Shine a narrow beam (laser pointer, or a phone torch through a slit)
**sideways** through each eprouvette in a dark room. The isopropanol emulsion will show a visible
**Tyndall beam**; the sunflower solution will show nothing. Tests "is it scattering?" directly, with no
colorimetry at all.

**E2 — the claim.** Four eprouvettes at once, same light, same day: green and brown oil × isopropanol
and sunflower, **matched pigment dose**. Judge the *pairs*, not the individual tubes. If the sunflower
pair separates and the isopropanol pair does not at equal dose, the mechanism is confirmed and the
archive's silence is explained rather than contradicted.

⚠ **Match the dose carefully.** Sunflower oil is far more viscous than isopropanol, so a capillary
delivers a different mass into each — otherwise concentration confounds the entire comparison.

⛔ **E3 as first written is unrunnable and has been replaced.** It said to measure the WIDTH of a narrow
lamp line under two solvents. **There is no such line in this beam.** Both candidates are DETECTOR
artefacts rather than optical features: 608–610 nm is a Bayer channel crossover (`DOC_lamp_rebuild.md`
§6), and the 473 nm "blue-pump edge" rises in **one or two samples** (0.15–0.29 nm against a 0.146 nm
grid step) — far below any plausible instrument linewidth — and sits at **472.5 nm in the REFERENCE and
473.1 nm in the SAMPLE of the same run**. An optical feature cannot move; a threshold where the dominant
Bayer channel switches moves with signal level, and 0.6 nm is that.

**E3 — ⭐ the split sample.** §7.16.4a leaves a chemistry hypothesis with every optical explanation
removed, and §12.6 leaves the cause unsettled. Both are limited by the same confound: 7 index-matched
fills of one oil pair against 72 isopropanol runs spanning a year, two rigs and a rebuild.

⇒ **Take ONE oil, prepare ONE dilution, split it, and put half into each solvent in the same session on
the same rig.** Report `area(624) / area(Soret)` — dose-free, so the split need not be perfect. Two
spectra, one evening, and every confound above disappears at once.

⚠ Run it on the **green** oil: its 624 band is the taller of the two, so the isopropanol arm is furthest
from the noise floor where §7.16.4b's problems live.
