# SPEC — Colour retrieval from the spectrum (five chips + HSL)

Status: **IMPLEMENTED 2026-07-19 (K1–K4 built, K5 rig "works so far"; see §4 as-built).** Settled with Edwin 2026-07-19. Scope = the
**DEV plugin** (measurement bench) for now; the machinery (colour util + `MetricFieldView` + renderers) is generic and
any plugin can reuse it. Pairs with [`SPEC_capture_quality.md`](SPEC_capture_quality.md) (fidelity — now good enough to
trust colour) and the evaluation/colour pipeline in `spectracsPy-core`.

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

### 1b. colorAbsorbed = option (A), locked

`colorAbsorbed` is the **literal CIE colour of the absorbance** (parameter-free; scale-invariance is automatic).
Consequence Edwin accepted: it reads in the **blue/violet family** (the colour of what the oil *absorbs*, ≈ complement
of the transmitted green) — a **reliable** discriminator (greener vs browner oil ⇒ different colorAbsorbed hue), just
not literally "green". The layperson gap is closed later by a **calibrated verdict word** (§6), not by changing the
colour. Rejected alternative **(B)** — concentration-normalised *perceived* colour (stays green) — needs a made-up
standard `A_std` that biases the chip; recorded, not chosen.

---

## 2. How colour is computed today (reference — unchanged)

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
