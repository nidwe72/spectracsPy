<!--
MASTER DOCUMENT — Spectracs light, pigment and solvent.
This markdown file is the SOURCE OF TRUTH. The PDF is generated from it:

    python3 docs/tools/build_sample_physics_pdf.py
    -> ../spectracs-docs/internal/Spectracs_LightPigmentSolvent.pdf

Never hand-edit the PDF. Edit here, re-run, commit both.
This is DOCUMENTATION, not a specification: it explains the physics and chemistry the instrument
depends on. It creates no work items. Where something is open it says so and points at the spec.
-->

# Light, Pigment and Solvent

*What is in the jar, and what it does to a photon.*

**Why this document exists.** Its companion *Capture Fidelity* covers the **instrument** — how a webcam is made
to yield a spectrum. This one covers everything *in front of* it: the light, the pigment, the
solvent and the suspended matter. They are complementary halves, and for a long time only the first
half was written down. That turned out to be a mistake: measured across a whole project, **the
sample contributes more error than the camera does**.

**Audience.** A chemist who wants to know what the numbers mean physically; a developer who needs to
know why the pipeline is shaped the way it is; and anyone reading a Spectracs report who asks what
is actually being measured. No code appears anywhere in this document.

**How to read it.** Chapter 1 stands alone. Chapters 2 and 3 are the textbook part — light, matter
and the pigments, none of it specific to us. Chapters 4 to 6 are where our particular sample gets
awkward, and are the most practically useful. Chapter 7 says what follows for the measurement.

**A note on numbers.** Where a figure comes from our own measurements it is marked *(measured)* and
the owning specification is named. Everything else is textbook physics or published chemistry, with
sources in the appendix.

<!--TOC-->

<!--PAGEBREAK-->

## 1. The short version

### 1.1 What the instrument is really doing

A lamp shines through a jar of diluted pumpkin oil. A grating spreads the transmitted light into a
spectrum, a camera photographs it, and the software divides that by the same measurement made
without oil in the beam. The result is **absorbance** — how much light the sample removed, wavelength
by wavelength.

Two features of the absorbance curve tell green oil from over-roasted oil: a strong band in the blue
near 440–460 nm, and a weak one in the yellow-green near 560–580 nm. Their **ratio** is the verdict.

### 1.2 The five things worth remembering

> **1. Absorbance is a logarithm, and that is why it is useful.** Doubling the concentration doubles
> the absorbance, whereas it does *not* halve the transmitted light. Beer–Lambert linearity is what
> makes the numbers comparable at all (§2.2).
>
> **2. A ratio of two absorbance bands is almost indestructible.** Concentration, path length, lamp
> brightness and camera gain all scale absorbance *uniformly*, and a ratio divides a uniform scale
> straight out. This is why a €30 camera can do quantitative work (§2.3).
>
> **3. What survives a ratio is anything ADDITIVE.** Stray light, dark current — and above all
> **scattering by suspended matter**. These add to both bands and do not cancel (§2.5, §5).
>
> **4. The sample is not a solution.** A few drops of oil in isopropanol is a *dispersion*: the two
> are only partly miscible, so the oil arrives as suspended droplets alongside waxes that never
> dissolve at all. That suspension scatters, and the scattering masquerades as absorbance (§4, §5).
>
> **5. The pigment chemistry is simple; the sample preparation is not.** Chlorophyll's two absorption
> bands and their fate on roasting are textbook. Everything difficult about this measurement lives in
> the jar, not in the molecule (§7).

### 1.3 The chain, in one paragraph

Chlorophyll in the seed absorbs blue and red light and transmits green — that is why fresh
Steirisches Kürbiskernöl is green. Roasting strips the magnesium out of the chlorophyll ring and the
molecule becomes pheophytin, which absorbs differently; more roasting degrades it further. So the
shape of the blue absorption relative to the yellow-green absorption carries the roast history.
Reading that shape requires diluting the oil, and diluting it into an alcohol produces a cloudy
suspension whose light scattering sits underneath the pigment signal and compresses it. Most of the
engineering effort in this project has gone into that last sentence.

<!--PAGEBREAK-->

## 2. Light and matter

### 2.1 What absorption actually is

A molecule absorbs a photon when the photon's energy matches the gap between two of the molecule's
electronic energy levels. The energy of a photon is `E = hc/λ`, so **the wavelength that gets
absorbed is set by the size of that gap** — a large gap absorbs blue light, a small gap absorbs red.

For the pigments that matter here the relevant electrons are those in **conjugated π systems**:
alternating single and double bonds over which the electrons are delocalised. The longer the
conjugated chain, the smaller the energy gap, and the redder the absorption. This one rule explains
most of plant pigment colour, including why the carotenes are yellow-orange and chlorophyll is green.

An absorption *band* rather than a sharp line appears because each electronic transition is dressed
with vibrational and rotational sub-levels, and in solution the surrounding molecules smear those
further. In a liquid at room temperature the result is a smooth hump tens of nanometres wide — which
is fortunate, because it means a modest instrument can resolve it.

### 2.2 Transmittance, absorbance and Beer–Lambert

Measure the light through the sample, `S`, and through the blank, `R`. The **transmittance** is their
ratio, and the **absorbance** is its negative logarithm:

```
T = S / R                    A = −log₁₀(T) = log₁₀(R / S)
```

Absorbance is the useful quantity because of the **Beer–Lambert law**:

```
A = ε · c · l
```

— absorbance is *proportional* to concentration `c` and to path length `l`, with `ε` the molar
absorption coefficient, a property of the substance at that wavelength. Transmittance is not
proportional to anything: halving the concentration does not double `T`.

> **Where it breaks down.** Beer–Lambert assumes the absorbers are independent, dilute, and that only
> absorption removes light. At high concentration molecules interact and `ε` shifts; and any **stray
> light** reaching the detector puts a floor under `S`, so `A` stops rising with concentration and
> flattens. That flattening — *stray-light compression* — begins in practice below about
> `T = 10 %`, i.e. `A ≈ 1`. Our strongest band sits close to that line *(measured;
> `SPEC_capture_quality.md` §16.11.8)*, which is why the working dilution is chosen to keep it just
> under.

### 2.3 Why a ratio of two bands is so robust

If two bands are measured on the same sample, then `c` and `l` are identical for both, and

```
A₁ / A₂  =  (ε₁ · c · l) / (ε₂ · c · l)  =  ε₁ / ε₂
```

**Concentration and path length cancel exactly.** So does anything else that multiplies the whole
curve — lamp brightness, camera gain, grating efficiency. What remains is a pure property of the
substance.

This is why the pumpkin verdict is a *ratio* and not an absolute absorbance. It is also why the
dilution recipe can be changed without recalibrating the verdict: measured across a 50 % change in
concentration, the ratio moves by well under 1 % on green oil *(measured;
`SPEC_capability_proof.md` §11.1)*.

### 2.4 What the reference cancels — and what it does not

Dividing by the blank is the single most important idea in the instrument. The lamp's own spectrum,
the sensor's sensitivity at each wavelength, the grating's efficiency, the lens's vignetting — all of
these appear **identically** in `R` and `S` and divide out exactly. That is why we do not need to
characterise the camera.

But the cancellation is **multiplicative only**. Three things survive it:

| survives the ratio | why | what we do |
|---|---|---|
| **additive light** — stray light, dark current | added after the sample, so it does not scale with `S` | dark measured and found negligible; stray light bounded by keeping `A ≲ 1` |
| **non-linearity** — the camera's gamma curve | a ratio of two *bent* numbers is not the ratio of the true ones | decode the curve before dividing |
| **anything that changed between R and S** — lamp drift, sensor warm-up, the jar moving | it was not the same instrument twice | measure R and S close in time, and don't disturb the jar |

### 2.5 Scattering is not absorption — but the detector cannot tell

An absorbing molecule converts the photon's energy. A **scattering particle** merely sends the photon
somewhere else. Physically these are completely different; optically, in a straight-through
measurement, they are indistinguishable — **light that does not arrive is recorded as absorbance,
whatever the reason.**

This matters far more than it sounds, and chapter 5 is devoted to it.

<!--PAGEBREAK-->

## 3. The pigments

### 3.1 Chlorophyll: two bands, one molecule

Chlorophyll is a **porphyrin** — a large flat ring of four nitrogen-containing subunits with a
magnesium ion at the centre — carrying a long hydrocarbon tail that makes it fat-soluble. Its
absorption spectrum has a characteristic two-part shape that all porphyrins share, explained by
Gouterman's four-orbital model:

| band | position *(chlorophyll a in solution)* | strength |
|---|---|---|
| **Soret band** (also called B) | ≈ 430 nm — blue | very strong |
| **Q bands** | ≈ 578 nm (Qx) and ≈ 662 nm (Qy) — yellow-green and red | weak, roughly 1/5 to 1/10 of the Soret |

**Blue and red are absorbed; green in between is transmitted.** That is the whole reason chlorophyll
is green, and the reason fresh pumpkin seed oil is green.

> **Where our two measurement windows sit.** Our blue window, 440–460 nm, is on the **red flank of
> the Soret band** — not its peak, which lies below our usable range. Our second window, 560–580 nm,
> most plausibly catches the **Qx** transition. The strong **Qy** band near 660 nm lies *outside* the
> capture range entirely — and its rising flank is exactly what we later found intruding into what
> was supposed to be a signal-free part of the spectrum *(measured;
> `SPEC_capability_proof.md` §2.1a)*. The physics and the surprise line up.

### 3.2 What roasting does — pheophytin

Heat and acid strip the central **magnesium ion** out of the chlorophyll ring, replacing it with two
protons. The product is **pheophytin**, and the conversion is why green vegetables turn olive-drab
when overcooked and why chlorophyll-containing oils brown with roasting.

Losing the metal changes the ring's electronic structure, and the spectrum changes with it: the Soret
band **shifts toward the blue and sharpens**, while the Q bands redistribute. Further degradation —
oxidation, ring cleavage — eventually destroys the conjugated system altogether and the absorption
becomes a featureless slope.

**This is the physical basis of the verdict.** The ratio of blue absorption to yellow-green
absorption tracks how much intact chlorophyll survives relative to its degradation products. It is a
*roast/freshness* index, not a measure of "browning" in the Maillard sense.

### 3.3 The carotenoids

The second pigment family is the **carotenoids** — β-carotene, lutein and relatives. These are long
conjugated polyenes with no ring metal, and they absorb in a broad three-peaked structure across
**400–500 nm**, with essentially nothing above about 520 nm. They are what makes carrot juice orange
and pumpkin flesh deep yellow.

For us they are mostly a nuisance: their absorption tail reaches into the region we would like to use
as a quiet baseline, and unlike the suspended matter of chapter 5, **it is real absorbance that no
amount of clarification will remove**.

### 3.4 Why pumpkin seed oil is green — or brown

Styrian pumpkin seed oil contains chlorophyll and its derivatives from the seed coat, together with
carotenoids. A fresh, gently pressed oil retains enough intact chlorophyll to look distinctly green
in a thin layer. Longer or hotter roasting pheophytinises it, and the green retreats.

The commercial question — *"was this oil over-roasted?"* — is therefore a question about a molecular
ratio, and that is a question a spectrometer is genuinely better at than an eye.

### 3.5 Dichromatism: green in a film, red in the bottle

Hold Kürbiskernöl in a thin film and it is green. Look through the bottle and it is deep red. Nothing
about the oil changed — **the path length did.**

This is **dichromatism**, and pumpkin seed oil is its textbook example. The oil has a narrow
transmission window in the green plus a broad one in the red. In a thin layer both get through and
green dominates because the eye is most sensitive there; as the path lengthens, the narrow green
window is extinguished exponentially faster than the wide red one, and red wins. Kreft and Kreft
quantified the effect as a **dichromaticity index**.

> **Why it matters practically.** Perceived colour depends on path length, so *"it looks green"* is
> not a measurement. It also means our transmission-derived colour swatches are dilution-dependent by
> construction, while absorbance-derived ones are not — a distinction the evaluation code takes care
> to keep *(`SPEC_color_retrieval.md`)*.

<!--PAGEBREAK-->

## 4. The sample: oil in a solvent

### 4.1 Why dilute at all

Neat pumpkin oil is effectively opaque across the pigment bands at any practical path length. To
bring the absorbance into the instrument's usable range — roughly `A = 0.1` to `1.0` — the oil must
be diluted perhaps thirty-fold. **The solvent is therefore part of the measurement, not a
convenience**, and the choice of solvent has consequences all the way to the verdict.

### 4.2 Oil and alcohol are only partly miscible

Pumpkin oil is a **triacylglycerol**: three long fatty-acid chains on a glycerol backbone,
overwhelmingly nonpolar. Isopropanol is *semi-polar* — a polar hydroxyl group on a small nonpolar
isopropyl group. "Like dissolves like" is a crude rule but here it bites: the two are only
**partially miscible**.

Such a pair has an **upper critical solution temperature (UCST)**. Above it they mix in all
proportions; below it there is a **miscibility gap** — a range of compositions where a single phase
is not stable and the mixture separates. Solubility rises with temperature up to the critical point.

> **Water is the hidden variable.** Adding water to the alcohol raises the critical temperature
> sharply, i.e. makes the solvent markedly worse. Isopropanol is **hygroscopic**, so an opened bottle
> takes up atmospheric water over months. A tired bottle of "99 %" is measurably worse at dissolving
> oil than a fresh one — and nothing on the label says so.

### 4.3 The ouzo effect

When a solution of oil in a *good* solvent is rapidly diluted with a *poor* one, the oil finds itself
suddenly far above its solubility and comes out of solution — not as a separated layer, but as a
cloud of **spontaneously formed droplets**, typically tens to a few hundred nanometres across. The
mixture turns milky within seconds without any stirring energy being supplied.

This is the **ouzo effect**, named for what happens when water is added to anise spirits. It occurs
in the metastable region between the binodal and spinodal curves of the phase diagram, and it needs
no surfactant.

Adding a few drops of oil to isopropanol is the same operation in miniature: the oil is locally
concentrated at the point of entry and is then diluted below its solubility. **What forms is not a
solution but a metastable dispersion.**

### 4.4 What happens next — ripening, coalescence, sedimentation

A fresh dispersion is not stable, and it does not simply sit there. Three processes run in parallel:

- **Ostwald ripening.** Small droplets have higher internal pressure and slightly higher solubility
  than large ones, so material diffuses from small to large. The droplets grow, and the population
  coarsens.
- **Coalescence.** With no surfactant to keep them apart, droplets that meet merge.
- **Sedimentation.** Once droplets are large enough, gravity wins over Brownian motion.

**And here they sink rather than float.** Oil is denser than isopropanol — about 0.92 against 0.785
g/mL — so the droplets fall. (In water the same droplets would cream upward; the direction is set by
the density difference, not by the oil.)

The rate follows **Stokes' law**:

```
v = (2/9) · Δρ · g · r² / η
```

The `r²` is the important part. Fine droplets settle imperceptibly; as ripening grows them, the
settling accelerates **non-linearly**. That is why a fresh dilution appears stable for a while and
then clears faster and faster — and why "how long has it stood?" is a question with a strongly
non-linear answer.

> **Observed here.** A fresh dilution's readings drift for the first ~15 minutes and then continue
> changing for hours, **non-monotonically**: our measured ratio falls over the first half hour and
> rises over eleven *(measured; `SPEC_capability_proof.md` §11.4a–f)*. Stirring an aged sample
> re-suspends the sediment and puts the reading straight back where it started.

### 4.5 Choosing a solvent: polarity and solvency are different axes

The useful and slightly counter-intuitive point: **how well a solvent dissolves oil is not the same
as how polar it is.**

- **Solvency** for a triglyceride tracks the **alkyl chain length** — a longer hydrocarbon tail on
  the solvent resembles the fatty-acid chains it has to surround.
- **Solvatochromic shifts** — the small movements of an absorption band caused by the solvent — track
  the **dielectric constant** `ε`.

These can be varied nearly independently, and that is a lever.

| solvent | ε (25 °C) | b.p. °C | flash pt °C | dissolves oil | polystyrene | field-usable |
|---|---|---|---|---|---|---|
| water | 78 | 100 | — | not at all | ✅ | — |
| **2-propanol** *(current)* | **≈ 17.9** | 82.6 | 12 | **marginal** | ✅ safe | ✅ drugstore |
| 1-propanol | ≈ 20.1 | 97.2 | 22 | better | ✅ safe | specialist |
| **1-butanol** | **≈ 17.5** | 117.7 | 35 | **good** | ✅ safe | specialist |
| n-heptane | 1.9 | 98.4 | **−4** | ideal | ⛔ swells + crazes | ⛔ hazardous |
| cyclohexane, isooctane | ≈ 2 | — | — | ideal | ⛔ cyclohexane **dissolves** it | ⛔ |

**1-butanol is the interesting one.** Its dielectric constant is essentially that of isopropanol, so
absorption bands should barely move — while its longer chain makes it a genuinely good triglyceride
solvent. Dissolution without solvatochromism. Heptane, at `ε = 1.9`, would shift the bands
substantially, attack the sample jar (§6.1), and introduce a flammability hazard no food producer
should be asked to keep on a shelf.

### 4.6 What the analytical literature actually uses

Standard methods for chlorophyll and carotenoids in edible oils read them in **cyclohexane**,
**hexane**, **carbon tetrachloride**, or **ethanol/isooctane** and **ethanol/heptane** mixtures.
Nobody uses neat isopropanol.

**The field converged on hydrocarbons precisely because they give a true solution** — no dispersion,
no scattering, no settling. Our choice of an alcohol is a deliberate trade for field usability, and
chapter 5 is the bill for it.

> **On waiting.** Two pieces of standard guidance are often quoted and neither applies to us.
> *"Measure turbid samples within ten minutes"* comes from **nephelometry**, where the particles
> *are* the analyte and settling loses the signal. *"Allow 10–15 minutes to equilibrate"* refers to
> thermal equilibration and colour development in wet-chemistry assays. Where particles are the
> **interferent**, as here, the standard practice is neither — it is **to clarify: filter or
> centrifuge before measuring**, then fit a baseline for whatever residual remains.

<!--PAGEBREAK-->

## 5. Turbidity: the pedestal

### 5.1 Scattered light is recorded as absorbance

Restating §2.5 because everything in this chapter follows from it: a straight-through spectrometer
measures **light that failed to arrive**. It cannot ask why. Light removed by scattering from a
suspended droplet is therefore added to the absorbance, exactly as though a pigment had absorbed it.

Because the scattering is broad and smooth in wavelength, it lifts the **whole** absorbance curve off
zero. We call that additive floor the **pedestal**.

### 5.2 Particle size sets the colour of the scatter

How the scattering depends on wavelength is governed by the particle size relative to the wavelength:

| regime | particle size | wavelength dependence | appearance |
|---|---|---|---|
| **Rayleigh** | much smaller than λ | **∝ λ⁻⁴** — strongly blue-biased | the blue sky; a faint blue haze |
| **Mie** | comparable to λ | weakly dependent, oscillatory | milky white |
| geometric | much larger than λ | essentially flat | white, opaque |

So the *shape* of the pedestal is a fingerprint of what is suspended: a λ⁻⁴ tilt points to
nanodroplets, a flat floor to micron-scale waxes and press fines. In principle this is measurable; in
our spectrum it is frustrated by the absence of a genuinely pigment-free window to fit through
*(`SPEC_capture_quality.md` §16.12.11)*.

### 5.3 How large it is here, and why it wrecks a ratio

Measured across eight independent sample preparations, the pedestal in our weaker measurement band
runs at **0.7 to 1.9 times the pigment signal itself** *(measured;
`SPEC_capability_proof.md` §11.4e)*. **The plinth is bigger than the statue standing on it.**

And it is specifically corrosive to a *ratio*, because adding the same amount `c` to numerator and
denominator drags any ratio toward 1:

```
true ratio        12.37 / 1.00                     = 12.37
with pedestal    (12.37 + 1.59) / (1.00 + 1.59)    =  5.39
```

The pigment did not change. The pedestal compressed the reading by more than half. **This is the
entire difference between the two pigment-ratio figures a Spectracs report prints** — one before the
baseline correction, one after — and it is why a baseline correction exists at all.

Note what this does to §2.3's reassuring algebra: a ratio is immune to everything *multiplicative*,
and turbidity is the classic *additive* offender. Robustness has a specific shape, and this is the
hole in it.

### 5.4 An accidental experiment: three years on a shelf

The clearest demonstration was not designed. Oils bought in 2023 and measured in 2026 had spent three
years in the bottle — during which the same sedimentation described in §4.4 quietly clarified them.
Fresh 2026 oils had not.

| | pedestal | run-to-run scatter |
|---|---|---|
| oils aged three years | **0.84** | 2.5 % |
| fresh oils | **1.72** | 14.5 % |

The aged oils carried **half** the scatter — and separated the two quality classes about **eight
times better** *(measured; `SPEC_capability_proof.md` §11.4e)*.

> **The lesson, and it is the most useful sentence in this document: sample clarity is a first-class
> instrument parameter.** It is not housekeeping. On the evidence above it is worth more than any
> optical or algorithmic improvement available to us.

### 5.5 Getting rid of it

Four routes, in rough order of attractiveness:

1. **A better solvent.** If the oil truly dissolves, there is nothing to scatter. This is why §4.5's
   distinction between polarity and solvency matters.
2. **Filtration.** A syringe filter removes anything above its pore size. Note the limit: ouzo
   nanodroplets at 50–200 nm pass straight through a 0.22 µm membrane, so a filter distinguishes
   *which* population is responsible as much as it removes it.
3. **Centrifugation.** Faster and consumable-free, at the cost of another instrument and a transfer
   step.
4. **Waiting.** Free, slow, non-monotonic, and it leaves the sediment in the vessel where any
   agitation will re-suspend it. The weakest of the four, and where we started.

> **A trap worth naming.** If the sample is mixed in one vessel and an aliquot is transferred to
> another for measurement, **the transfer is itself a sampling step out of a settling dispersion**.
> How much suspended matter travels with the aliquot depends on when and from what depth it was
> drawn. Homogenise before drawing, or clarify after; doing neither leaves a large, invisible
> sample-to-sample variable *(`SPEC_capability_proof.md` §11.4f)*.

<!--PAGEBREAK-->

## 6. The vessel

### 6.1 Plastics and solvents

The sample sits in a small transparent jar. Which materials survive contact is decided by the same
"like dissolves like" rule as §4.2, now working against us:

| material | alcohols | aliphatic hydrocarbons | note |
|---|---|---|---|
| **polystyrene** | ✅ resistant | ⛔ **attacked** | cheap, optically clear, what we use |
| PET / PETG | ✅ | mostly ✅ | good general compromise |
| polypropylene | ✅ | fair, swells slowly | translucent, poor optically |
| PTFE / FEP | ✅ | ✅ | inert to essentially everything |
| borosilicate glass | ✅ | ✅ | inert, but see §6.5 |

**Alcohols are essentially the only organic family polystyrene tolerates.** That couples the solvent
and the vessel into a single decision: stay with alcohols and the cheap clear jar keeps working; move
to a hydrocarbon and the vessel must be replaced too.

### 6.2 Putting a number on it: Hansen parameters and RED

Compatibility charts like the one above are qualitative, and at the margins they are unreliable —
published charts contradict one another on cases such as acrylic against aliphatics. **Hansen
solubility parameter theory replaces the judgement with arithmetic.**

The idea is that "like dissolves like" can be made three-dimensional. Every substance gets three
coordinates: `δD` for dispersion forces, `δP` for polar interactions, `δH` for hydrogen bonding. A
*polymer* is not a point but a **sphere** of radius `R₀` — the region of that space whose solvents
dissolve it. The distance from a solvent to the polymer's centre is

```
Ra² = 4·(δD₁ − δD₂)² + (δP₁ − δP₂)² + (δH₁ − δH₂)²
```

*(the factor 4 on the dispersion term is empirical — it is what makes the solubility region come out
spherical rather than ellipsoidal)*, and the useful quantity is that distance scaled by the sphere:

```
RED = Ra / R₀              "Relative Energy Difference"
```

| RED | meaning |
|---|---|
| **< 1** | inside the sphere — the solvent dissolves the polymer |
| **≈ 1** | on the boundary — swelling, crazing, environmental stress cracking |
| **> 1** | outside — a non-solvent |

Against **polystyrene** (δD 21.3, δP 5.8, δH 4.3, R₀ 12.7):

| solvent | **RED** | reading |
|---|---|---|
| toluene | **0.65** | dissolves it |
| **cyclohexane** | **0.90** | **dissolves it** — the classic theta-solvent for polystyrene |
| n-heptane | **1.10** | just outside — swells and stress-cracks, does **not** dissolve |
| **1-butanol** | **1.23** | outside — safe; the closest of the alcohols |
| isooctane | 1.27 | outside |
| **2-propanol** | **1.29** | outside — safe |
| 1-propanol | 1.33 | outside |
| ethanol | 1.49 | comfortably outside |
| water | 3.23 | inert |

Three things worth taking from that table:

- **The alcohols are not borderline.** Butanol at 1.23 against isopropanol's 1.29 is a small
  difference well outside the sphere, not a near-miss.
- **Aliphatic hydrocarbons do not dissolve polystyrene** — heptane at 1.10 swells and crazes it. The
  practical verdict is the same, but the mechanism is not, and confusing the two leads to the wrong
  test.
- **Cyclohexane, which the analytical literature favours for oil pigments, is the worst possible
  choice for a polystyrene vessel** — at 0.90 it is a genuine solvent for it. A reminder that the
  best solvent for the *sample* and the best for the *container* are separate questions.

> **⚠ Do not mix parameter sets.** Published values differ by a few percent, and polystyrene's `δD`
> is quoted as either ≈ 18.6 or ≈ 21.3 depending on convention. Combining a solvent from one set with
> a polymer from another produces confidently wrong answers. The *ranking* is robust; treat absolute
> values as indicative and always compare within a single source.

### 6.3 Crazing, and why the failure mode is optical

The realistic failure is not a dissolved jar. It is **environmental stress cracking**: a marginal
liquid plus the frozen-in stress of an injection-moulded part, producing a network of fine surface
crazes. It is cumulative in exposure time, and it starts where the stress is highest — around
threads and gate marks rather than in the middle of a wall.

**A crazed vessel does not crack. It goes very slightly hazy.** And haze scatters light, which this
instrument records as absorbance (§5.1).

> **This is the nastiest failure mode in the whole document**, because a slowly crazing jar would
> look exactly like sample turbidity — the very thing one changes solvent to remove. The experiment
> and its control would degrade together, and the conclusion drawn would be that the new solvent had
> not worked.
>
> The check is cheap and uses the instrument itself: cycle a spare vessel through twenty
> fill-and-empty cycles at realistic contact time, then **measure it as a blank against an unexposed
> one**. A raised baseline is crazing, detected far below the threshold of the eye.

### 6.4 Refractive index, reflections and the meniscus

Every interface between two materials of different refractive index reflects a little light. For
light arriving straight on, the reflected fraction is

```
R = ((n₁ − n₂) / (n₁ + n₂))²
```

| interface | n₁ → n₂ | reflected |
|---|---|---|
| liquid → **air** | 1.377 → 1.00 | **2.5 %** |
| liquid → polystyrene | 1.377 → 1.59 | 0.5 % |
| liquid → borosilicate | 1.377 → 1.47 | 0.1 % |
| liquid → **FEP film** | 1.377 → 1.344 | **0.015 %** |

Two things follow. First, **a closely index-matched window is almost invisible optically** —
fluoropolymer film against an alcohol reflects a hundred and fifty times less than a liquid–air
surface. Second, and more importantly, a liquid–air surface is a **meniscus**: a curved surface whose
shape changes with fill level, wetting and tilt. It is a lens that is slightly different every time.
Eliminating it — by letting a window contact the liquid — removes a variable, not just a reflection.

### 6.5 The awkward geometric constraint

Because the light passes through the vessel *and* its lid, **both must be transparent** — and a clear
vessel with a matching clear lid is not something one simply buys in glass. The practical answer is a
lid with an aperture carrying a clamped **fluorinated ethylene propylene (FEP)** film: better than
95 % transmission across the visible, under 2 % haze, and chemically immune to everything discussed
here. It must be **clamped, never glued** — the non-stick nature that makes it solvent-proof also
means nothing adheres to it.

<!--PAGEBREAK-->

## 7. What follows for the measurement

Six consequences, each traceable to a chapter above.

1. **Measure a ratio, never an absolute absorbance.** Concentration, path length and every
   multiplicative instrument property cancel (§2.3). This is the foundation everything else rests on.
2. **Keep the strongest band below about `A = 1`.** Beyond that, stray light flattens the response
   and the band stops reporting concentration honestly (§2.2).
3. **Treat sample clarity as an instrument parameter with its own error budget.** On our own
   measurements it is worth more than any optical improvement currently available (§5.4).
4. **Prefer clarifying to waiting.** Settling is slow, non-monotonic, and reversible with a knock
   (§4.4, §5.5). The analytical literature does not wait; it filters.
5. **Choose the solvent on two axes, not one.** Solvency for a triglyceride follows chain length;
   band shifts follow dielectric constant. They can be traded independently, and a good choice gets
   dissolution without moving the bands (§4.5).
6. **Remember that the vessel and the solvent are one decision.** Polystyrene and alcohols go
   together; hydrocarbons require replacing both (§6.1–6.2). And watch the vessel optically, not
   structurally — a crazing jar mimics a turbid sample (§6.3).

> **What is still open.** Whether a better solvent removes the pedestal in practice; how much of the
> remaining sample-to-sample variation is preparation rather than instrument; and whether a window
> reaching past 700 nm — where the strong chlorophyll band lies, and where a genuinely
> pigment-free region would finally exist — is worth the optical change. These are owned by
> `SPEC_capture_quality.md` §16.12 and `SPEC_capability_proof.md` §11.4.

<!--PAGEBREAK-->

## Appendix — sources and further reading

**Absorption spectroscopy and Beer–Lambert.** Any physical-chemistry text; the treatment here follows
the standard one. Porphyrin band structure: M. Gouterman, *Spectra of porphyrins*, J. Mol. Spectrosc.
**6** (1961) 138 — the four-orbital model that names the Soret and Q bands.

**Chlorophyll and its degradation.** Pheophytinisation and the colour of cooked greens are covered in
any food-chemistry text. Pumpkin-specific composition: Fruhwirth & Hermetter (2007), *Seeds and oil
of the Styrian oil pumpkin*, Eur. J. Lipid Sci. Technol. **109**(11) 1128–1140,
[10.1002/ejlt.200700105](https://doi.org/10.1002/ejlt.200700105).

**Dichromatism.** S. Kreft & M. Kreft, on the dichromaticity index and pumpkin seed oil as its
type example.

**Oil–alcohol miscibility.** Rao & Arnold (1957), *Alcoholic extraction of vegetable oils IV —
solubilities of vegetable oils in aqueous 2-propanol*, JAOCS,
[10.1007/BF02637892](https://doi.org/10.1007/BF02637892). The critical-solution-temperature data
behind §4.2.

**The ouzo effect.** Vitale & Katz (2003) for the original characterisation; for a modern direct
observation of the droplet nucleation, *ACS Central Science* (2023),
[10.1021/acscentsci.2c01194](https://pubs.acs.org/doi/full/10.1021/acscentsci.2c01194).

**Scattering.** Rayleigh and Mie regimes: any optics text. For the practical spectroscopic
consequence, see the turbidity-correction literature on baseline fitting.

**Analytical methods for oil pigments.** A spectrophotometric method for plant pigments,
[Chem. Papers](https://link.springer.com/article/10.2478/s11696-013-0502-x); and the standard
cyclohexane-based determinations of olive-oil chlorophylls and carotenoids.

**Materials and solubility.** C. M. Hansen, *Hansen Solubility Parameters — A User's Handbook*
(2nd ed., CRC Press 2007) — the three-parameter model, the polymer-sphere construction and the RED
metric of §6.2, together with the tabulated values used there. Polystyrene and PMMA
chemical-compatibility charts are also in circulation but disagree on marginal cases; prefer the
parameter calculation, and soak-test rather than trust either. FEP optical data,
[AdTech transmission tables](https://adtech.co.uk/technical-data/fep-uv-transmission-data/).

**Our own measurements**, wherever marked *(measured)*: `SPEC_capability_proof.md` §11 and
`SPEC_capture_quality.md` §16, with the underlying reasoning in `KB_spectroscopy_physics.md`.
The instrument half of the story is in the companion document, *Capture Fidelity*.
