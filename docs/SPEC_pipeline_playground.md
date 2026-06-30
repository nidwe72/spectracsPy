# SPEC — Pipeline Playground (test/dev bench)

> Status: **DESIGN (spec-first; implement on explicit request only).** A master-only top-level view that
> runs the full spectral pipeline as a **flat strip of per-step tabs**, with **synthetic** REFERENCE and
> SAMPLE. It is the dev shortcut for what the pumpkin **plugin** will do, and the place to **test the
> stability claim**. Builds on `SPEC_measurement_evaluation_concept.md` (the sound pipeline),
> `KB_spectroscopy_physics.md`, `KB_led_and_oil_spectra.md`. Overlaps Roadmap **#5** (virtual-device
> images) and **#6** (absorption + evaluation).

---

## 1. Goal & scope

- One **tab per pipeline step**: synthesize REFERENCE → synthesize SAMPLE → transmission/absorption →
  evaluate→colour. "This test does what the plugin should do" — a known-provenance, fully-controlled
  bench (every parameter ours; **no captured/unknown data**).
- **Reuse the same utility methods the plugin will use** (`SpectrumUtil`, `SpectralColorUtil`) + new
  reusable **ops** — so the playground *is* the first real implementation of #6's building blocks.
- **Kept** (not throwaway) — useful for calibration sanity, LED-set selection, and regression.

**Non-goals:** the end-user nested wizard (this is a flat dev strip); persistence of runs; the plugin
loader / role-filtered end-user mode. Numeric verdict thresholds (deferred — need real captures).

## 2. Tabs ↔ phases (does not contradict the settled model)

| Tab | Phase · step | Produces | View |
|---|---|---|---|
| **(a) Reference** | ACQUISITION · reference | `C{reference:[R]}` | LED picker + live SPD plot |
| **(b) Sample** | ACQUISITION · sample | `C{sample:[S]}` | oil preset + model knobs + SPD plot |
| **(c) Process** | PROCESSING | `C{transmission:[T], absorption:[A]}` | T and A plots |
| **(d) Evaluate** | EVALUATION | `EvaluationResult` | swatch + perfect-green sample + hue/L/S + verdict |

Each tab is a sub-view; the playground page is a `PageWidget` whose single main-container widget is a
`QTabWidget` (mirror `SpectralJobsWidgetViewModule`). Tabs read the previous tab's `SpectraContainer`.

## 2a. Next concrete build — the **Setup** tab (three images + target colours)

**This is the first thing to implement** and the deliverable of the current task: **display the virtual
device's three images in the playground**, plus the target-colour swatches. It realises Roadmap **#5**
(grow `VirtualSpectrometerSettings` from **one** image slot to **three**).

A **"Setup" tab group** with **4 inner tabs**:

| Inner tab | Shows | Source |
|---|---|---|
| **Calibration** | `testSpectra/cfl_philips_calibration.png` — a CFL capture whose sharp **Hg/phosphor lines** (~405, 436, 487, 542/546, 611 nm) give the **pixel→nm polynomial** | existing calibration |
| **Reference** | the synthesised **LED reference** capture image | tab (a) SPD → rasterise via the polynomial |
| **Sample** | the synthesised **oil sample** capture image | tab (b) SPD → rasterise |
| **Target colours** | the demo swatches **EXCELLENT / GOOD / BAD** (hue ≈ 100 / 80 / 45°, §6) | concept demo anchors |

**Goal of *this* step:** just **render the three images + the target swatches** — proving the three-slot
virtual device and the synthesis→image rasterisation end-to-end. The downstream pipeline tabs (§3–§6)
then consume the spectra acquired from these images.

> **"3×4 tabs" — my reading:** the **3 device images + 1 target-colours = 4 inner tabs** of this Setup
> group (alongside the 4 pipeline tabs in §2). **Confirm** if you meant a literal 3×4 grid / different
> nesting — flagged for the next discussion.

## 3. Tab (a) — REFERENCE synthesis (the LED bench)

- A **LED picker**: the Avonec catalogue (`KB_led_and_oil_spectra.md` §1) as toggleable entries, each
  with a **per-LED SPD**. **Primary source = the shop's MEASURED spectrum** (digitised from the
  Spektralmessung JPG) — confirmed available, incl. the **warm-white** (a bimodal blue-pump ~448 +
  phosphor ~586 shape that a Gaussian cannot represent → measured is mandatory for whites). **Fallback
  = skewed-Gaussian** (peak, FWHM, skew) only for any *coloured* LED whose JPG isn't harvested. **luxpy
  is not needed** for the default set (measured curves cover it); keep it optional. Per-LED **weight**
  (drive power).
- `R(λ) = Σ weightᵢ · SPDᵢ(λ)`, plotted **live** (pyqtgraph). Default set: 2× warm-white + hyper-violet +
  royal-blue + green + red + deep-red (candidates: blue 455, amber 590–610).
- **Decide the LED set empirically here:** toggle LEDs, watch (i) gap-free coverage and (ii) intensity in
  the diagnostic bands 430–480 / 520–560 / 630–670. This *is* how the final set gets chosen (§ "two
  missing LEDs" discussion).
- Output: `SpectraContainer{reference:[R]}`.

## 4. Tab (b) — SAMPLE synthesis (the physical oil model)

- **Synthetic, known-provenance.** `S(λ) = R(λ) · 10^(−A_oil(λ) · c·l)` where
  `A_oil(λ) = chlorophyll(Soret≈430, Q≈665) + carotenoid/lutein(≈440–480) + browning(↗ short-λ)`.
- **`c·l` (concentration × path) is the primary green→brown knob** (Beer–Lambert dichromatism); a
  **browning amplitude** adds the roast axis.
- **Presets, not free sliders** (per decision): named oils — e.g. **`EXCELLENT`** (clean green window, low
  browning) and **`BAD/over-roasted`** (high browning, higher `c·l`) — each a fixed parameter set with an
  **expected HSL** (you provide the targets). The tab shows the resulting `S` SPD and the achieved HSL
  vs the target (a pass/fail bench). Model knobs are visible (read-only or advanced) for inspection.
- Output: `SpectraContainer{sample:[S]}` (with `inputs=[reference container]`).

## 5. Tab (c) — PROCESS (transmission + absorption)

- Condition R and S (`smooth → removeBaseline → rebin 380–780 → normalize`), then:
  **`T = S/R`** (`TransmissionOp`) and **`A = −log10(T)`** (`AbsorptionOp`).
- Plot **T** and **A**. (T is what feeds colour; A is the absorption fingerprint/plot.)
- Output: `SpectraContainer{transmission:[T], absorption:[A]}`.

## 6. Tab (d) — EVALUATE (colour + verdict)

- **`QColor = SpectralColorUtil.spectrumToColor(T)`** (fixed D65 → LED-independent; §concept) → measured
  **hue / lightness / saturation**.
- Render the `EvaluationResult` view-models: **`ColorSwatch`** (measured), **`ColorSample`(s)** (the
  reference anchors), **`Label`** (hue/L/S), **`Verdict`** (band → GREEN/PERFECT/BROWN/UNDER). First
  concrete take on **`EvaluationResult` → GUI rendering** (a deferred design thread).
- **Demo verdict thresholds (provenance-clean):** derive the hue band boundaries from the **synthetic
  presets' own achieved hues**. Self-consistent, fully owned, no captured data. (Real thresholds still
  need provenance-known captures — concept §8.)

  **Demo hue anchors & bands** (provisional; hue in degrees = `colorsys` hue × 360; **higher hue =
  greener = better**, lower = browner. Rendered at fixed lightness 0.20):

  | Preset / band | Target hue | Reads as |
  |---|---|---|
  | `EXCELLENT` preset | **~100°** | fleshy fresh green |
  | `GOOD` preset | **~80°** | green / yellow-green |
  | `BAD` preset | **~45°** | brownish (over-roasted) |

  | Verdict band | Rule | Label |
  |---|---|---|
  | hue ≥ **90°** | fresh green | **PERFECT** |
  | **70–90°** | green | **GOOD** |
  | **55–70°** | yellowing | **ACCEPTABLE** |
  | hue < **55°** | brown | **OVER-ROASTED** |

  Tune the SAMPLE oil model (`c·l`, browning) in tab (b) until each preset lands on its target hue; the
  band edges (55°, 70°, 90°) then sit between the presets. All clearly **DEMO/provisional**.
- **The `oilScores.svg` colours (`#669900`/`#446600`/`#223300`) are display anchors only — NOT threshold
  seeds:** they are **hue-degenerate** (all hue ≈ 80°, differing only in lightness 0.30/0.20/0.10), so
  they encode quality as *darkness*, not the green→brown *hue* our pipeline discriminates on. Fine as
  stylised perfect/good/bad swatches next to the measured one; useless for hue cut-points.

## 7. Calibration honoured via the image path (delivers Roadmap #5)

To genuinely exercise ROI + calibration (your requirement), the synthetic spectra round-trip through the
**existing acquisition**:
1. Synthesize `R`/`S` SPD (tabs a/b).
2. **Rasterise** onto the calibration ROI as a grayscale strip: for each ROI pixel column `x`, `nm =
   poly(x)`, `gray = clamp(scale · SPD(nm))` → a synthetic capture **image**.
3. Store as the **virtual device's REFERENCE / SAMPLE image** — growing `VirtualSpectrometerSettings`
   from **one** image slot to **three** (calibration / REFERENCE / SAMPLE) = **Roadmap #5**.
4. The **existing** `ImageSpectrumAcquisitionLogicModule` reads it back (applies the polynomial) → the
   `Spectrum`. So calibration is real, not bypassed; one effort builds both the playground and #5.

(A lighter "sample directly on the calibration nm-axis" mode may exist as a shortcut, but the image path
is the faithful default.)

## 8. Reuse vs greenfield

| Reuse (implemented) | New (greenfield, plugin-SDK-shaped ops) |
|---|---|
| `Spectrum`, `SpectraContainer` (fix dup-`__init__`) | `LedReferenceSynthesisOp` (LED SPDs → R) |
| `SpectrumUtil` mean/smooth/removeBaseline/rebin/normalize | `OilSampleSynthesisOp` (R + oil model → S) |
| `SpectralColorUtil.spectrumToColor` / `getColorDifference` | `TransmissionOp` (S/R), `AbsorptionOp` (−log10) |
| `ImageSpectrumAcquisitionLogicModule`, calibration poly | `VerdictOp` (hue → band); `EvaluationResult` view-model rendering |
| `QTabWidget` pattern, `PageWidget`, nav registration | LED-SPD harvest (measured JPG → peak/FWHM/skew or digitised) |

Ops are plain `SpectraContainer → SpectraContainer` so the pumpkin plugin reuses them verbatim.

## 9. Stability check (a first-class feature)

A control to **swap/perturb the LED set** and observe the verdict: with reference-normalization the hue
should barely move (concept §4). Surfacing "verdict Δ vs LED change" turns the bench into a **proof** of
LED-independence — and a guard against regressions.

## 10. Placement & registration

- **Master-only** top-level **"Playground"** view, reached from a Settings → Administration (or Tools)
  button, gated on `CurrentUserSession().hasRole(MASTER_USER)` (mirror the User-admin gate).
- Register like any page: instantiate + `addWidget` in `MainViewModule`; add the target to both chains in
  `NavigationHandlerLogicModule`; launch button emits the `NavigationSignal`.

## 11. Open / deferred

- **Final LED set** — decided empirically in tab (a). **Full Avonec measured set already harvested** to
  `spectracs-references/leds/avonec/` (410–660 colours + all whites). The only gap, **390–410 UV-A (no
  measured spectrum published), is synthesised with luxpy** (or a skewed-Gaussian) if that LED is used.
- **Verdict thresholds** — for the demo, derived from the synthetic presets' achieved hues (§6); real
  thresholds deferred until provenance-known captures exist (concept §8).
- **`SpectraContainer` dup-`__init__` bug** — fix when first used.
- **luxpy dependency** — only if we use its white-LED/mixing builders; otherwise skewed-Gaussian keeps it
  dependency-light. Decide at build time.

## 12. Build phases (for the eventual implementation request)

1. Ops in `-model` (`LedReferenceSynthesisOp`, `OilSampleSynthesisOp`, `TransmissionOp`, `AbsorptionOp`,
   `VerdictOp`) + unit tests (synthesize → T/A → colour → verdict; LED-swap stability assertion).
2. LED-SPD harvest util (measured JPG params or digitised) + the Avonec default set.
3. Playground `PageWidget` + `QTabWidget` + the four sub-views (pyqtgraph plots, swatch).
4. Virtual-device three-image slots (#5) + the rasterise-to-ROI image path.
5. Master-only registration + nav.
