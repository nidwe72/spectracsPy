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

## ⭐⭐⭐ The verdict metric is `Rv` — and this document is why  *(2026-08-25)*

```math
R_{v} = 100\,\frac{A_{624} - A_{valley}}{A_{Q} - A_{valley}}
\qquad
T = 52 \quad \text{(higher = greener)}
```

⭐ **The demetallation this document is about is not background to the metric. It IS the metric.**

### The chain, in four steps

**1 · The pigment.** Pumpkin seed oil's green is **protochlorophyll**, and storage and roasting convert it
to **protopheophytin** by stripping the central magnesium — the speciation §4.1 sets out, with
protopheophytins running 1.1–35.5 % of protochlorophylls and rising with seed storage.

**2 · What losing the magnesium does to the spectrum.** A metallated ring has **D₄ₕ** symmetry and shows
**two** Q bands. The free base drops to **D₂ₕ** and shows **four**, numbered I–IV from the longest
wavelength. Gouterman's four-orbital model classifies their intensity ordering into four types by
substituent pattern — etio, rhodo, oxo-rhodo, phyllo — and **band I is the weakest in every one of them**.
Protopheophytin carries the ring-E carbonyl, a rhodofying group, so *rhodo* (III > IV > II > I) is the
expected ordering here.

⇒ **A pigment whose longest-wavelength band dominates while metallated ends up with that band the weakest
of four once the magnesium leaves.**

**3 · Which band is ours.** Our 624 nm feature **is band I**. So demetallation should collapse it while
intensity moves to shorter Q components — and that is measurable as a *ratio between two Q bands*, with no
reference to anything outside the porphyrin system.

**4 · What was measured.** Standard-normal-variate over 500–627 nm, nine fills, three oils:

| | pigment state | predicted | measured |
|---|---|---|---|
| green oil | protochlorophyll, **Mg in** | long-λ band dominant | **624 nm is the tallest feature**, *z* ≈ 2.2 |
| brown oils | protopheophytin, **Mg out** | band I weakest of four | **569 nm tallest** (*z* ≈ 2.75); 624 falls to *z* ≈ 0.5–0.75 |

The two classes **cross over** — the green and brown means intersect at 541 and 558 nm — which is what a
two-species conversion produces, and what §4.9's ligand argument would predict if the conversion is what
is varying between oils.

### ⭐⭐ Why the Soret is the wrong denominator — and this document already said so

The metric `Rv` replaces divided by the 448–460 nm Soret window. `DOC_lamp_410_680.md` Figure 5:

> the carotenoid absorption at ~455 nm rides on top of the Soret, so the peak you can see is not the peak
> the chemistry is at

**Carotenoids have no Q bands and are not tetrapyrroles.** Their concentration varies with cultivar,
season and pressing — for reasons unconnected to roasting. So the old metric divided a porphyrin band by a
window belonging to a different pigment family, and Gouterman's account governed only its numerator.

`Rv` keeps both terms inside **one chromophore's Q manifold**. That is the mechanistic reason it survives a
40–45 % dose change and three different solvents where the Soret-normalised metric moves 6.5 units on a
single oil.

### ⚠ Three caveats that must travel with this argument

1. ⛔ **Q-manifold conservation is untested, not shown.** If demetallation only *redistributed* intensity,
   total Q per unit Soret would be constant across oils. Measured, it reads 7.85 / 5.56 / 6.71 — not flat.
   ⚠ But the denominator is that same carotenoid-contaminated Soret, so this is not a clean test either
   way. **Untested, not refuted.**
2. ⛔ **The band assignment is literature, not this instrument.** §4's own 2026-08-04 warning stands: *"OUR
   OWN INSTRUMENT DOES NOT CONFIRM THE Qy POSITION, and cannot at this range."* The clamp ends at 630 nm
   and cannot see whether a band sits at 660.
3. ⛔ **Consistency is not mechanism.** Two *different pigments* in differing proportions would produce the
   same crossover as one pigment changing symmetry. Separating them needs the red extension, or a
   deliberate demetallation of one fill re-measured against itself.

⛔ **Status: `Rv` is chosen, not built.** The Soret-normalised metric still computes the verdict until it
lands. Contract: `SPEC_red_ratio_metric.md`; full treatment `DOC_metric_algebra.md` **chapter 4a**.

## 1. The short version

### 1.1 What the instrument is really doing

A lamp shines through a jar of diluted pumpkin oil. A grating spreads the transmitted light into a
spectrum, a camera photographs it, and the software divides that by the same measurement made
without oil in the beam. The result is **absorbance** — how much light the sample removed, wavelength
by wavelength.

Three features of the absorbance curve tell green oil from over-roasted oil: a strong band in the blue
near **448–460 nm**, a weak one in the yellow-green near **565–580 nm**, and the flat **500–560 nm**
valley between them. The verdict is the yellow-green band measured **above that valley** and scaled by the
blue one — a difference over a level, not a ratio of two bands (`DOC_metric_algebra.md` §5.1).

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
> **scattering by suspended matter**. These add to both bands and a ratio cannot remove them (§2.5, §5).
> ⭐ Which is exactly why the shipped metric is a **difference** over a level rather than a ratio of two
> bands: a difference cancels a *flat* pedestal outright. ⚠ Real Mie scattering has spectral **slope**, and
> that part still survives (§5.2).
>
> **4. The sample is not a solution.** A few drops of oil in isopropanol is a *dispersion*: the two
> are only partly miscible, so the oil arrives as suspended droplets alongside waxes that never
> dissolve at all. That suspension scatters, and the scattering masquerades as absorbance (§4, §5).
>
> **5. The pigment chemistry is simple; the sample preparation is not.** The pigment's two absorption
> bands and their fate on roasting are textbook — once you have the right molecule, which is
> **protochlorophyll**, not chlorophyll (§3.1). Everything difficult about this measurement lives in
> the jar, not in the molecule (§7).

### 1.3 The chain, in one paragraph

The pigment in the seed — **protochlorophyll**, chlorophyll's biosynthetic precursor — absorbs blue and
red light and transmits green, which is why fresh Steirisches Kürbiskernöl is green. Roasting strips the
magnesium out of the ring and the molecule becomes **protopheophytin**, which absorbs differently; more
roasting degrades it further. So the
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
most of plant pigment colour, including why the carotenes are yellow-orange and the chlorophylls green.

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

⭐ **The shipped metric uses this for its DENOMINATOR only.** `Q%` divides by the Soret band, which is what
makes it dilution-invariant — but its numerator is a **difference** of two windows rather than a second
band, because that is what removes the additive half of the problem (item 3 above). One nuisance each:
the division kills what multiplies, the subtraction kills what adds.

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

### 3.1 The molecule in our jar is PROTOchlorophyll — not chlorophyll

This matters more than a prefix suggests, so it is worth being precise about.

**Both molecules are tetrapyrroles**: a large flat ring built from four nitrogen-containing subunits,
with a magnesium ion held at the centre and a long hydrocarbon tail (phytol) that makes the whole
thing fat-soluble. The difference is one bond.

| | ring D | class | consequence |
|---|---|---|---|
| **chlorophyll** *a* | **reduced** (C17–C18 saturated) | a **chlorin** | strong, far-red Qy band |
| **protochlorophyll** *a* | **not reduced** | a **porphyrin** | Qy ~40 nm further to the blue, and weaker |

![**Figure 1** — the macrocycle, and the single bond that separates the two molecules. Four pyrrole subunits (A–D) hold a magnesium ion between their four nitrogens; ring D carries the phytol ester that makes the pigment fat-soluble. In **protochlorophyll** the C17=C18 bond in ring D is intact, so the ring system is a **porphyrin**. In **chlorophyll** that one bond is reduced — two hydrogens added — making it a **chlorin**, and moving the red absorption band ~40 nm further into the red. Schematic: substituents and the isocyclic ring E are omitted.](figures/pigment_macrocycle.svg)

Protochlorophyll is chlorophyll's biosynthetic *precursor* — the plant reduces that one ring to make
chlorophyll. In the Styrian oil pumpkin's seed coat the reduction never happens, so the precursor
accumulates. Fruhwirth & Hermetter identify the oil's colourants as **protochlorophyll (a and b)** and
**protopheophytin (a and b)**.

### 3.2 Where the bands come from — Gouterman's four orbitals

All porphyrin-type spectra have the same two-part shape, and one model explains it. Gouterman (1961)
showed that the visible spectrum is governed by just **four frontier orbitals** — two nearly-degenerate
occupied and two nearly-degenerate empty ones. Their combinations give:

| band | transition | character |
|---|---|---|
| **Soret** (also **B**) | S₀ → S₂ | **very strong**, blue, ~430–440 nm |
| **Q** | S₀ → S₁ | **weak** — 1/5 to 1/10 of the Soret — yellow-green to red |

**Blue and red are absorbed; the green in between is transmitted.** That is the whole reason these
pigments are green, and the reason fresh pumpkin seed oil is green.

#### Why the Q region has more than one peak — and what Qx / Qy mean

In a **metallo**porphyrin the magnesium sits on a four-fold symmetry axis (D₄ₕ). The two Q transitions
are then **degenerate** — same energy, polarised at right angles to each other in the plane of the ring.
What you see is one Q band plus a **vibronic satellite** at higher energy, conventionally labelled
**Q(0,0)** (the origin, longest wavelength — also called α) and **Q(1,0)** (one quantum of vibration
added — also called β).

**Remove the metal and the symmetry drops to D₂ₕ.** The two protons that replace Mg²⁺ sit on one axis,
so the ring is no longer four-fold symmetric, the degeneracy is **lifted**, and the two transitions
separate into distinct bands — now properly called **Qx** and **Qy** after their polarisation axes.
Each keeps its own vibronic satellite, so a metal-free (free-base) tetrapyrrole shows **four** Q bands,
numbered **I to IV from the longest wavelength**: I = Qy(0,0), II = Qy(1,0), III = Qx(0,0), IV = Qx(1,0).

> **A word on "degenerate".** In spectroscopy *degenerate* means two states happen to share the same
> energy — it carries no sense of decay. Symmetry is what enforces the sharing, so lowering the symmetry
> **lifts** the degeneracy and the states separate. The pigment is not "degenerating"; its energy levels
> are ceasing to coincide.

**⭐ And the redistribution has a direction.** Free-base porphyrin spectra are classified into four types
by their Q-band intensity ordering — *etio* (IV > III > II > I), *rhodo* (III > IV > II > I),
*oxo-rhodo* and *phyllo*. **Band I — the longest-wavelength band — is the weakest in every one of them.**
So a pigment whose long-wavelength Q band *dominates* while it holds its magnesium finds that same band
demoted to the weakest of four once the magnesium goes. Intensity moves toward the blue. That is not a
guess; it is the standard classification, and §3.4 shows it is what we measure.

![**Figure 2** — what losing the magnesium does. **Left:** with Mg on the four-fold axis (D₄ₕ) the two in-plane transition dipoles *x* and *y* are equivalent, the Q states are degenerate, and the spectrum shows one Q origin plus its vibronic satellite. **Right:** the two protons that replace Mg sit on one axis only (D₂ₕ), so *x* and *y* are no longer equivalent, the degeneracy is lifted into separate Qx and Qy states, and **four** Q bands appear where there were two. Free-base band numbering I–IV runs from the longest wavelength. Since demetallation is exactly what roasting does, this split is the spectroscopic signature of the degradation we measure.](figures/pigment_qband_symmetry.svg)

> **⭐ This is the single most useful idea in this chapter.** *Losing the magnesium is exactly what
> roasting does* (§3.3). So the **appearance of a Qx/Qy split is itself the spectroscopic signature of
> the degradation we are trying to measure.** The green→brown axis is not merely "less pigment" — it is
> a change in the *symmetry* of the surviving pigment, and symmetry changes rearrange bands rather than
> just shrinking them.

#### The numbers, for the molecule we actually have

| | Soret | Q region | fluorescence |
|---|---|---|---|
| chlorophyll *a* *(textbook default — **not** ours)* | ≈ 430 nm | ≈ 578, **≈ 662 (Qy)** | ≈ 668–675 nm |
| **protochlorophyll(ide) *a*** *(ours)* | **≈ 432–440 nm** | minor bands ≈ 505, 535, 606; **Qy(0,0) ≈ 623–626** | **≈ 630–636 nm** |

The protochlorophyll figures are for alcoholic/acetone solution, which is what we measure in. They are
corroborated from inside the oil itself: Fruhwirth & Hermetter record the oil's fluorescence maximum at
**635 nm**, and a fluorescing molecule emits ~10 nm to the red of the transition it absorbs on — putting
the absorber at ~625 nm and nowhere near chlorophyll's 662.

#### Where our three measurement windows sit

| window | sits on | confidence |
|---|---|---|
| **440–460 nm** | the **red flank of the Soret band** — not its peak, which is below our usable range | solid |
| **560–580 nm** | a band in the **Q region**; the specific assignment is **open** — see below | ⚠ open |
| **600–630 nm** | the approach to **Qy(0,0)** at ~623–626, plus the minor ~606 band | good |

> **⚠ An honest gap: we do not know what the 560–580 band is.** Two candidates, and they are not
> equivalent. It could be the **vibronic Q(1,0) satellite of the intact, Mg-containing protochlorophyll**;
> or it could be a **Qx band of protopheophytin**, the metal-free degradation product, which only exists
> *because* of the split described above. The published protochlorophyllide minor bands (505, 535, 606 nm)
> do not obviously include it, which mildly favours the second reading — but the oil contains both
> molecules plus carotenoids, and no source we have assigns this band.
>
> **Why it matters:** the 565–580 window is the **numerator** of the shipped verdict metric, `Q%` — it
> rises into brown. ⚠ It was the *denominator* of the Pigment Index that shipped until 2026-08-21, where
> it fell into brown instead; the sign of every statement about this band therefore depends on which
> metric is being discussed. If it is a degradation-product band the physical justification is much
> stronger than we currently claim, whichever way up it is read. **This is worth one measurement to settle** — and unusually,
> a hint already exists in our own data: relative to the 560–580 band, the 600–630 Qy flank is
> substantially *weaker* in brown oil than in green (ratio 0.58 vs 0.69), which is what you would expect
> if 600–630 tracks the intact pigment more specifically than 560–580 does. Suggestive, not conclusive.

### 3.3 What roasting does — protopheophytin

Heat and acid **strip the central magnesium ion out of the ring**, replacing it with two protons. The
product is **protopheophytin**.

**Where the name comes from.** *Pheo-* is from the Greek *phaiós*, "dusky" — **pheophytin** is
literally "the dusky plant pigment", the colour a chlorophyll turns once it loses its magnesium. It is
the same reaction that makes overcooked greens go olive-drab. *Proto-* marks the unreduced ring D of
§3.1. So the two prefixes describe **two independent modifications**, and there are four molecules:

![**Figure 3** — the pigment family. Two independent changes, four molecules. Down the page: whether ring D is reduced (§3.1) — the difference between a porphyrin and a chlorin. Across the page: whether the magnesium is still held — the difference roasting makes. Our oil contains the **top row**: protochlorophyll and, as it degrades, protopheophytin. Ordinary leaf chlorophyll and its degradation product occupy the bottom row and are shown only for orientation.](figures/pigment_four_molecules.svg)

**Why protopheophytin matters here, and why it has moved to the centre of the story.** It was named in
the source all along — Fruhwirth & Hermetter list the oil's colourants as *"protochlorophyll (a and b)
and protopheophytin (a and b), the latter being a protochlorophyll lacking the magnesium ion"*. What is
new is the evidence that it is **spectroscopically active inside our measurement window**, which is
§3.4.

It is not only roasting that makes it. In pumpkin seeds, protopheophytins accumulate as a **storage**
degradation product and have been reported anywhere from **1 % to 36 %** of the protochlorophylls. That
wide natural range is the chemical quantity the verdict is ultimately reading — and it is why the oil's
history, not only its roast, shows up in the measurement.

Spectroscopically this is the D₄ₕ → D₂ₕ symmetry drop of §3.2: the Soret **weakens and shifts toward the
blue**, and the Q region **gains structure** as the degeneracy lifts. Further degradation — oxidation,
ring cleavage — eventually destroys the conjugated system altogether and the absorption decays to a
featureless slope.

**⭐ This is the physical basis of the verdict, and it is worth stating in its strongest form.** We are
**not** measuring "how green the oil is", nor even "how much pigment is left". We are measuring the
**ratio of two chemical species** — intact protochlorophyll against its magnesium-free degradation
product protopheophytin. Roasting and storage move that ratio; the ratio moves the spectrum; we read the
spectrum.

That is a stronger and more falsifiable claim than "less pigment", and the data insists on it: across our
two classes the **total** Q-region absorbance is essentially identical (0.2300 vs 0.2251) while the
*shape* differs at *d* = 10.3. Nothing is missing — something has been **converted**. It is a
*roast/freshness* index, not a measure of "browning" in the Maillard sense.

### 3.4 Why this shows up as a change of SLOPE, not of level

Spectroscopically the D₄ₕ→D₂ₕ drop of §3.2 does something specific: it **redistributes** the Q
intensity rather than removing it. One tall origin band becomes several smaller ones spread toward the
blue. Total Q-region absorbance barely changes — which is exactly what we measure *(green 0.2300 vs
brown 0.2251 over 560–580; `SPEC_capture_quality.md` §16.13)*.

So why does our 600–630 window see such a large difference? **Because that window is narrow and sits on
a flank, not on a peak.**

![**Figure 4** — the mechanism. **Top:** with the magnesium intact, one dominant Q origin sits just past our capture limit, so the far red — and with it the **620–630 baseline anchor** — stands **high**, and the line fitted through the two anchor windows is **steep**. **Bottom:** once the magnesium is gone, that same intensity is spread across several weaker bands further to the blue; nothing tall is left near 630, the anchor drops, and the same line goes **nearly flat**. The total area under the two curves is similar; only its distribution differs. **The two solid bars are the only numbers the instrument takes from the curve** — one mean per anchor window — and the dashed line through them is the baseline it subtracts. ⚠ Schematic — the degraded band positions are illustrative, and with no turbidity pedestal modelled the contrast is exaggerated against the measured 1.65×; the two near anchors differ here where the real ones nearly coincide, so **compare the right-hand ends.**](figures/pigment_far_window_slope.svg)

**The slope across a narrow window reports the height of the nearest peak, not the amount of pigment.**
That is the whole answer. A tall band whose edge crosses the window gives a steep rise; move that
intensity 30–50 nm to the blue and split it, and the window is left on flat ground — even though just as
much light is being absorbed overall, a little further to the blue.

This makes the far window an unusually specific probe: it responds to *whether the intact, symmetric
pigment is still there*, and is comparatively blind to how much total pigment the oil contains.

⚠ **Measured, and it is not a concentration effect.** Under simple Beer–Lambert the two classes' curves
would differ only by a scale factor, so any ratio taken *inside* the Q region would be identical for
both. Measured on the two post-rebuild sets, the 620–630 rise divided by the Q band's own amplitude is
**0.427 for green against 0.080 for brown — a factor of 5.3, at *d* = 10.3**. Scaling is excluded; the
shape genuinely differs. *(`SPEC_capture_quality.md` §16.13.)*

#### ⚠ Why we do not simply *look* at the two-versus-four bands — and it is not the instrument

The natural objection is that we are inferring a band structure we cannot see, and that a better
spectrometer would settle it. **It would not.** Measured on our own data:

| | |
|---|---|
| grid spacing | 0.146 nm per bin, 1305 bins across 440–630 nm |
| narrowest feature we resolve *(473 nm lamp artifact)* | **FWHM 1.0 nm** |
| second artifact *(607 nm registration)* | **FWHM 2.7 nm** |
| the Q bands we would need to separate | **20–30 nm wide** |

The rig **out-resolves the target by ten to twenty times**. Four other things stand in the way instead:

1. **Window truncation — the dominant limit.** Our capture stops at 630 nm and the longest-wavelength
   band sits at ~623–630. We see a flank and nothing beyond it.
2. **The two species always coexist.** Real oil is a mixture (protopheophytin 1–36 %), so a pure
   two-band or pure four-band spectrum is never presented to us — only their superposition.
3. **Intrinsic linewidth.** At room temperature in solution these bands are 20–30 nm wide and overlap
   heavily. Even with a perfect instrument and an unlimited window, the four free-base bands appear as
   partly merged shoulders, not four clean peaks.
4. **The turbidity pedestal**, which contributes 52–61 % of the Q band's height and flattens what
   contrast remains.

**⇒ The remedy is a wider window, not a finer one.** That single conclusion redirects an entire class of
"buy better hardware" thinking toward a much cheaper change.

#### ⚠ What is measured, and what is inferred

| link | status |
|---|---|
| the pigments are protochlorophyll and protopheophytin | **sourced** |
| roasting and storage strip the magnesium | **sourced** |
| losing the metal lifts the degeneracy: two Q bands become four | **deduction** from symmetry |
| free-base band I is the weakest ⇒ long-wavelength intensity falls | **sourced** (the four-type classification) |
| the two classes' Q-region shapes genuinely differ | **measured**, *d* = 10.3 |
| the cause is *specifically* demetallation | ⚠ **best available explanation, not a controlled result** |

The last row is the honest weak point: these are two different **bottles**, which differ in more than
their protopheophytin content. Note what survives if it is wrong — the *speciation* reading holds
regardless; only the *mechanism* would need replacing.

**The experiment that would close it is cheap.** Take one oil, split it, and deliberately demetallate
half — acidification is the standard laboratory route. Same bottle, same turbidity, same dilution, one
variable. If the 600–630 slope collapses in the acidified half, the causal link stops being an
interpretation and becomes a measurement.

> ⭐ **Read the slope on BOTH windows when that run happens.** The 620–630 anchor replaced 600–630 on
> 2026-08-03 (`SPEC_capture_quality.md` §16.20). ⚠ **Neither is shipped any more** — both belong to the
> Pigment Index, which became `DOC_metric_algebra.md`'s Appendix E on 2026-08-21. The prediction above is
> about the *pigment*, so it is anchor-agnostic and stands as written; record both windows anyway, because
> the diagnostics compute them for free and because §3.4a's version of this experiment reads a third pair
> (565–580 and 623–626) that neither anchor covers.

### 3.4a ⭐⭐ The see-saw — the same mechanism, as two numbers  *(2026-08-21)*

§3.3 says roasting **redistributes** oscillator strength rather than destroying it, and §3.4 says that
shows up as a change of slope. Both are statements about a mechanism. This section is the same claim
turned into two numbers that can be read off any spectrum we hold.

Measure the two red features the **same way** — each as a height above the flat valley, scaled by the
Soret flank, so both are concentration-free and directly comparable:

```
   h(568) = 100 x [ A(565-580) - A(500-560) ] / A(448-460)
   h(624) = 100 x [ A(623-626) - A(500-560) ] / A(448-460)
```

Class means over the **88 labelled isopropanol runs** of the report archive (55 green / 33 brown;
diffuser-IN runs and the opaque fill excluded):

| | `h(568)` | `h(624)` | sum | half-difference |
|---|---|---|---|---|
| green oils | 15.80 | 12.78 | **28.58** | 1.51 |
| brown oils | 20.00 | 7.55 | **27.55** | 6.22 |

⭐ **The split changes completely; the total barely moves.** Browning adds 4.2 units at 568 nm and takes
5.2 away at 624 nm — and the sum of the two ends stays within 3.6 % of itself. That is what a
**conversion at roughly constant total pigment** looks like, and it is §3.3's mechanism stated as a
measurement rather than as an inference from symmetry.

![**Figure 5** — the see-saw. **Left:** the mechanism — the same plank, tipped further as the magnesium leaves. **Right:** the same thing as the numbers a metric actually uses. Each band bar is a common grey **pivot** — half the total, and nearly identical for both classes — plus a coloured cap at 568 nm and exactly the same amount taken away at 624 nm. A metric that reads one end collects one of the two class gaps; a metric built as a **difference** collects both and discards the pivot. ⚠ The "tilt" drawn here is not the shipped `dQ100`, which uses a different denominator; see the figure's own footnotes.](figures/tilt_seesaw.svg)

#### ⭐ The coupling changes SIGN between the two levels — and that is the whole argument

Correlating the two band heights across the archive gives opposite answers depending on what is being
varied, and the disagreement is the point:

| what varies | correlation `r(h568, h624)` | what it means |
|---|---|---|
| **between oils** *(20 oil means)* | **−0.832** | **which pigment** — a conversion redistributes a fixed budget, so one end rises as the other falls. The plank **tips** |
| **within one oil's repeat fills** *(pooled)* | **+0.811** | **how much pigment**, and how the light got there — concentration, path, re-seating, turbidity all scale or offset the whole spectrum. The plank **lifts** |

⭐⭐ **The sign tells you which of the two you are looking at.** Compare *different oils* and the bands move
**apart**; compare *repeat fills of one oil* and they move **together**. Nothing else in the measurement
separates *which pigment* from *how much pigment*, and this costs nothing to read.

⭐ **It is also what shows the effect is chemistry and not arithmetic.** Both heights are divided by the
same `A_Soret`, so it is fair to ask whether the anti-correlation is just an artefact of that shared
division. It is not, and the reason needs no subtlety: **dividing two numbers by the same thing moves them
the same way** — make the divisor smaller and *both* heights grow. A divisor artefact can therefore only
ever produce a **positive** correlation. That is exactly the sign we see *within* a fill, and the opposite
of the one we see *between* oils. One division cannot make both signs at once, so something other than the
division is moving the bands apart.

⭐ **And there is nothing in the divisor to do it with anyway** — the Soret barely differs between the
classes:

| across the 20 oil means | green | brown | Cohen's *d* |
|---|---|---|---|
| $A_{Soret}$ — the shared denominator | 0.7522 | 0.7777 | **+0.16** |
| $A_{Q} - A_{valley}$ — the numerator | 0.1185 | 0.1551 | **+1.43** |

⚠ **Theory says demetallation should *weaken* the Soret (§3.2). We cannot see that.** At *d* = 0.16 the
Soret is class-blind on this instrument, and the small sign it does carry runs the other way. Dose
dominates it, and dose is not a class property. ⇒ the shared denominator cannot be manufacturing the
coupling in either direction — but neither is it evidence *for* the mechanism, and §3.2's prediction
remains untested here.

#### ⭐ The conserved quantity, and what it is good for

If this is a conversion, some weighted sum of the two ends should be far steadier across oils than either
end alone. Measured over the 20 oil means:

| quantity | spread across oils | separates green from brown? |
|---|---|---|
| `h(568)` alone | CV **13.4 %** | yes, Cohen *d* = **+2.78** |
| `h(624)` alone | CV **30.6 %** | yes, *d* = **−2.28** |
| `h(568) + 0.68 · h(624)` | CV **5.4 %** | ⛔ **no** — *d* = **+0.28** |
| `h(568) + h(624)` *(unweighted)* | CV **6.5 %** | — |

⭐ **The individual bands carry the composition; their sum is conserved and nearly class-blind** — 5.7×
steadier than the noisier band, and it cannot tell a green oil from a brown one. That is an **empirical
stand-in for an isosbestic point**: a total-pigment reference that does not care how far the conversion
has gone. ⚠ Note the unweighted sum scores almost as well as the fitted one, so the effect is not a
knife-edge fit.

⚠ **What this is and is not evidence for.** It is consistent with a two-species conversion and it is the
clearest such signature the archive contains. It is **not** proof: oils could differ in total pigment and
in composition in a correlated way; the 0.68 weight is fitted on the same 20 oil means it is scored on;
and ⛔ **no true isosbestic point exists inside our 440–630 nm window** — searched for and not found, which
is itself expected if the chlorophyll→pheophytin isosbestic lies near 660–680 nm, outside the clamp.

⭐⭐ **It sharpens §3.4's acid experiment into a falsifiable prediction.** That run was specified as
*"does the 600–630 slope collapse in the acidified half?"* — a directional check. The see-saw says more
than direction: acidify one half of a split fill and **`h(568)` must RISE, `h(624)` must FALL, and their
SUM must stay put.** A conversion has to conserve the sum; a solvent artefact, a turbidity change or a
dilution error would not. Same bottle, same turbidity, one variable — and now three predictions instead
of one.

### 3.5 The carotenoids

The second pigment family is the **carotenoids** — β-carotene, lutein and relatives. These are long
conjugated polyenes with no ring metal, and they absorb in a broad three-peaked structure across
**400–500 nm**, with essentially nothing above about 520 nm. They are what makes carrot juice orange
and pumpkin flesh deep yellow.

For us they are mostly a nuisance: their absorption tail reaches into the region we would like to use
as a quiet baseline, and unlike the suspended matter of chapter 5, **it is real absorbance that no
amount of clarification will remove**.

### 3.6 Why pumpkin seed oil is green — or brown

Styrian pumpkin seed oil contains chlorophyll and its derivatives from the seed coat, together with
carotenoids. A fresh, gently pressed oil retains enough intact chlorophyll to look distinctly green
in a thin layer. Longer or hotter roasting pheophytinises it, and the green retreats.

The commercial question — *"was this oil over-roasted?"* — is therefore a question about a molecular
ratio, and that is a question a spectrometer is genuinely better at than an eye.

### 3.7 Dichromatism: green in a film, red in the bottle

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

| solvent | ε (25 °C) | b.p. °C | flash pt °C | dissolves oil | polystyrene | usable here |
|---|---|---|---|---|---|---|
| water | 78 | 100 | — | not at all | ✅ | — |
| methanol | ≈ 33 | 64.7 | 11 | **poor** — the most polar of the alcohols | ✅ safe | ⛔ **acutely toxic, skin-absorbed** *(§4.7)* |
| ethanol | ≈ 24.5 | 78.4 | 13 | poorer than isopropanol | ✅ safe | ⚠ **§4.9 — a ligand candidate, not a solvency one** |
| **2-propanol** *(in use, and staying)* | **≈ 17.9** | 82.6 | 12 | **marginal** | ✅ safe | ✅ **chosen** |
| 1-propanol | ≈ 20.1 | 97.2 | 22 | better | ✅ safe | ⛔ H318 |
| **1-butanol** | ≈ 17.5 | 117.7 | 35 | **good** | ✅ safe | ⛔ **H318** |
| 2-butanol | ≈ 16 | 99.5 | 24 | between the two above | ~ caution | ⛔ not pursued |
| acetone | ≈ 20.7 | 56.1 | **−20** | good | ⛔ **dissolves it** | ⛔ not pursued |
| n-heptane | 1.9 | 98.4 | **−4** | ideal | ⛔ swells + crazes | ⛔ hazardous |
| cyclohexane, isooctane | ≈ 2 | — | — | ideal | ⛔ cyclohexane **dissolves** it | ⛔ |
| **de-arom. white spirit** | ≈ 2 | 145–200 | **≈ 40–60** | **ideal** | ⛔ dissolves it | ⚠ **§4.8 — reopened** |

**In principle a longer-chain alcohol is the interesting direction.** Its dielectric constant is close
to isopropanol's, so absorption bands should barely move, while its longer chain makes it a better
triglyceride solvent — dissolution without solvatochromism.

⭐ **And the reverse direction is not the mirror image of it** *(2026-08-21)*. A *shorter* alcohol — ethanol,
methanol — is **more** polar, so it dissolves the oil less well and would coarsen the emulsion rather than
clear it. What it buys lies on a different axis entirely: a smaller molecule is a better **fifth ligand** for
the pigment's magnesium (§4.9). The two axes pull in opposite directions, which is the likeliest reason
§4.7's standard methods reach for a **mixture** rather than for either end of the alcohol series.

### 4.6 ✅ The decision: isopropanol stays  *(⚠ still the shipping answer — but see §4.8, which reopens the hydrocarbon half of it)*

**The instrument keeps 2-propanol and its existing polystyrene vessel.** Not because the alternatives
were untested in principle, but because each fails on a specific, checkable ground — and because the
problem the swap would solve stopped being the one that limits the instrument.

| candidate | why it is not used |
|---|---|
| **1-butanol** *(and 1-propanol, isobutanol)* | **H318 — "causes serious eye damage", Category 1: irreversible.** For an instrument meant to be operated by a miller in food premises, that is the wrong classification to accept. *(tert-butanol is excluded separately: it melts at 25.8 °C and is a solid at room temperature.)* |
| **2-butanol** | The one butanol both liquid at room temperature and free of Cat-1 eye damage — but a **branched** alcohol, so its solvency gain over isopropanol is only partial; more volatile; and its ε near 16 rather than 17.8 weakens the very "bands barely move" argument that made a butanol attractive. Not enough gain for the disruption. |
| **acetone** | Chemically appealing — 80 % acetone is the *standard* solvent in the pigment literature (§3.2), so it would place our band positions directly on the published scale. But it **dissolves polystyrene**, so it demands a new vessel, and no suitable one exists (§6.6). |
| **n-heptane, cyclohexane** | Ideal solvents, but they attack the vessel and carry hazards no food producer should be asked to keep on a shelf. |

**And the reason the question is closed rather than merely deferred:** the solvent work existed to
reduce the scattering pedestal — that is, to buy **precision**. Precision is no longer what limits this
instrument. The measured separation between a green and a brown oil is roughly **eleven standard
deviations**, with no overlap between any two runs *(`SPEC_capture_quality.md` §16.13)*. What limits
the instrument now is whether the **threshold** dividing the two classes is in the right place — a
question no solvent can answer, and which a solvent change would actively set back, since every band
position and therefore the threshold itself would have to be re-derived.

> ⚠ **One condition attaches.** All of that rests on the *sample-preparation* scatter being modest, and
> that quantity has not yet been measured (§5.5's aliquot trap). If it turns out to be large, turbidity
> becomes the limiting term again and the solvent question genuinely reopens.
>
> ⭐ **And a second condition surfaced later, from a different direction — §4.8.** The argument above rests
> on turbidity not being the limiting term. That rests in turn on a measurement whose interpretation has
> since been questioned: the re-seating scatter that we attribute to the *holder* was measured on a
> **turbid** sample, and nobody has checked what it would be in a clear one.
>
> ⭐⭐ **And §4.9 makes the case this table never made — the case FOR isopropanol** *(2026-08-21)*. Everything
> above decides the solvent by **elimination**. After the white-spirit evening there is a positive argument as
> well, and the surprising half of it is that the emulsion chapter 5 treats as the bill we pay is also what
> makes dilution-invariance **structural**.

### 4.7 What the analytical literature actually uses

Standard methods for chlorophyll and carotenoids in edible oils read them in **cyclohexane**,
**hexane**, **carbon tetrachloride**, or **ethanol/isooctane** and **ethanol/heptane** mixtures.
Nobody uses neat isopropanol.

**The field converged on hydrocarbons precisely because they give a true solution** — no dispersion,
no scattering, no settling. Our choice of an alcohol is a deliberate trade for field usability, and
chapter 5 is the bill for it.

⭐⭐ **And the paper this document's pigment chapter is built on reads its spectra in METHANOL**
*(added 2026-08-21, after the claim that methanol is a poor choice was queried at the bench)*. Fruhwirth &
Hermetter (2007) say so in the Fig. 3 caption — *"All spectra were recorded in methanol"* — and Fig. 3C
describes *"a methanolic solution of Styrian pumpkin seed oil"*. So methanol is a perfectly good
spectroscopic solvent for **exactly our sample**, and a flat claim that it dissolves oil badly is *true
about the molecule and wrong about the measurement*. What separates the two is concentration:

| | oil in the cell | regime |
|---|---|---|
| Fruhwirth, laboratory UV/Vis | micrograms, very high dilution | far below any solubility limit — methanol holds it |
| **our §16.23 recipe** | 120 µL into 10 mL = **1.2 % v/v** | 10–100× more concentrated; this is where solubility bites |

⇒ **at their dilution methanol is fine; at ours it would be worse than isopropanol.** ⛔ It is still not a
candidate: acutely toxic and absorbed through the skin, which ends the discussion for an instrument operated
in food premises.

⚠ **But one consequence deserves following up, and it is not cosmetic.** If Fruhwirth's methanolic sample is
a **true solution**, then Fig. 3A is the right comparison for a **white-spirit** run and not for one of ours
in isopropanol. `spectracs-references/comparisons/fig3A_vs_spectracs/` records the paper's Q band at
**573.8 nm** against a 2026-07-16 isopropanol run at **572.9 nm**, and calls that a ~1 nm reproduction. Two
things have happened since. `KB_spectroscopy_physics.md` §4.1a moved our Q band to **568 nm**; and the
2026-08-21 re-reading of the archive found that the apparent 573–580 nm maximum in every isopropanol run is
the **~581 nm Bayer channel crossover** — a 2 nm-wide feature, far too narrow to be an electronic band of a
large molecule in room-temperature solution — while the four white-spirit fills, the only true solutions we
have measured, read **568**. ⇒ the "reproduces to ~1 nm" agreement may be **two artefacts meeting**.
⛔ **Open. This document does not resolve it**, and the candidate explanations — a pixel digitisation of
Fig. 3A, methanol against a hydrocarbon, our own wavelength calibration — are not separated.

> **On waiting.** Two pieces of standard guidance are often quoted and neither applies to us.
> *"Measure turbid samples within ten minutes"* comes from **nephelometry**, where the particles
> *are* the analyte and settling loses the signal. *"Allow 10–15 minutes to equilibrate"* refers to
> thermal equilibration and colour development in wet-chemistry assays. Where particles are the
> **interferent**, as here, the standard practice is neither — it is **to clarify: filter or
> centrifuge before measuring**, then fit a baseline for whatever residual remains.

### 4.7a What those methods actually compute — and the one thing they do better than we do  *(2026-08-29)*

It is worth being concrete about what the standard methods *do* with the spectra they record, because two of
their choices bear directly on this instrument and one of them is better than ours.

They read pigments through two- or three-wavelength photometric formulas with published extinction
coefficients: carotenoids as a lutein equivalent at **470 nm**, chlorophylls as pheophytin *a* at **670 nm**,
each divided by a coefficient and the path length and multiplied by a gravimetric dilution factor. The
chlorophyll form is the interesting one, because it does not read the peak bare — it reads

```
A(670) − ½ · [ A(630) + A(710) ]
```

a band height against the **mean of two flanking anchors**, and the anchors are there for exactly the reason
chapter 5 gives: oil scatters, and the scatter is a smooth pedestal under everything. ⭐ **That is the same
construction the metrics in this project use** — arrived at from turbidity in edible oil rather than from the
pedestal work of chapter 5, which is a pleasant kind of agreement.

Three things follow for us, and they are not all comfortable.

**The formula itself is unreachable.** Both the 670 nm band and its 710 nm anchor lie outside our window.
There is a widely offered workaround for a red-clamped instrument — abandon 670 and compare the bare
absorbance at ~610 nm between oils — and it must be refused, because it silently drops the anchors that made
the original formula work. On this instrument the pedestal is the majority of a raw band height. A
red-clamped spectrometer does not need a different wavelength; it needs the anchors kept.

**The absolute numbers are convention-bound.** Two published bases for the same chlorophyll measurement
differ by nearly a factor of two, because they report different reference pigments. A concentration in mg/kg
from photometry is comparable only to other numbers computed the same way — which is the same caution this
project has already learned about its own thresholds.

⭐ **And the blank is better than ours.** The standard method zeroes the instrument on **pure solvent from
the same bottle used to dilute**, so the matrix — its own faint absorbance, its own scattering, its own
refractive index — cancels out of every sample. We reference against the *lamp*, so the solvent rides
through. That mattered little when the solvent was isopropanol and nearly transparent. It matters more now
that the solvent is sunflower oil (§4A), a pigmented material with batch-to-batch variation we have already
measured. The apparatus for it mostly exists: a reference on pure solvent is already taken with every fill.
⏸ Turning that into a true matrix blank is a change to the measurement convention and is not proposed here —
it is recorded as the one place where the older, slower, laboratory practice is simply right and we are not.

`KB_spectroscopy_physics.md` §9 carries the formulas, the coefficients, and the two constants worth checking
before anyone quotes them.

### 4.8 The hydrocarbon route, reconsidered  *(2026-08-19)*

§4.7 ends by admitting that the analytical field converged on hydrocarbons because they give a true
solution, and that our alcohol is a deliberate trade whose bill is chapter 5. It is worth asking, once,
what happens if we stop paying that bill.

The candidate is **de-aromatised white spirit** — the odourless isoparaffin sold in every hardware
shop — or, for a shipped method, a defined substance such as **isooctane**. Either dissolves the oil
completely and clear at room temperature.

**What that would remove is not a detail.** The emulsion, the scattering pedestal of chapter 5, the
waiting for a fill to clear, the warm bath, the cloud point, and the whole apparatus by which the
instrument decides *when* a sample has settled and *which* of its own looks to report — all of it exists
because the oil does not dissolve in isopropanol. A solvent that dissolves it retires the lot. The lamp
dose per measurement would fall from minutes to about seventeen seconds, and with it the photodamage
that the settling read was built to work around.

**Three objections that used to close this question have since weakened.**

*The red end.* The strongest argument against a non-polar solvent was that the pigment's red band sits
at 623–626 nm against a detector that stopped at 629.8 — no room for a solvatochromic shift, and the
shift direction is not predictable for a magnesium pigment. Both halves have moved. The capture window
now reaches **635.9 nm**, and the **verdict** metric never looks past **580 nm** — `Q%` reads 448–460,
500–560 and 565–580. ⚠ But `dQ100`, printed beside it as a scalar since 2026-08-21, reads **623–626**, and
§3.4a's see-saw is built on that band — so the red-end argument still bites, just not the number that
carries the pill.

*The hazard.* De-aromatised white spirit carries an aspiration classification that isopropanol does not.
But it is an **ingestion** hazard — the danger is swallowing and then aspirating, which is why the case
literature is unlabelled bottles and siphoned fuel, not workshop use. Against that, isopropanol flashes
at **12 °C** and white spirit at **40–60 °C**, and it is the alcohol whose vapour sits inside its
flammable range on a warm bench. On the risk that a workshop actually meets, the hydrocarbon is the
safer of the two.

*The mixture.* A petroleum distillate is not a defined substance, which ought to disqualify it from a
method that must compare across years. Except that saturated hydrocarbons have no chromophore above
about 280 nm, so batch-to-batch variation is **optically invisible** across our whole 400–636 nm window.
One protocol line — blank and sample from the same bottle — closes it.

**What is genuinely uncertain is smaller than any of those, and more interesting.**

The first question is whether the jar goes *optically clear* or merely *less cloudy*. A hydrocarbon
dissolves the waxes beautifully; it is a poor solvent for the **phospholipids**, whose head groups are
polar, and for the press fines. Fixing the waxes is not the same as fixing the turbidity.

The second is a coordination question. The magnesium at the centre of the pigment wants a fifth ligand.
In an alcohol the solvent provides one and the pigment stays as single molecules; in a rigorously dry
hydrocarbon it can take that ligand from a *neighbouring pigment molecule* instead, forming dimers whose
bands are shifted and broadened. Because that is an equilibrium, the spectrum would then depend on
concentration — and a metric built on dilution-invariance cannot survive that. Four things argue it will
not happen here: our pigment is present at a few **micromolar** where the effect is a millimolar
phenomenon; the dissolved oil supplies roughly ten thousand ester carbonyls per pigment molecule, and
any ligand in excess breaks the aggregates; up to a third of the pigment pool is protopheophytin, which
has no magnesium at all; and hardware-shop solvent is not dry — the water it carries is itself a ligand.

**And one possibility that runs the other way.** In the present system the pigment is almost certainly
not dissolved in the isopropanol at all: it is lipophilic, and it sits inside the oil droplets. Diluting
such a sample makes *more droplets*, not different ones, so each pigment molecule's surroundings never
change — which may be part of why the metric is so indifferent to dilution. In a true solution that is
no longer automatic. It is a reason to measure rather than to assume.

**The measurement that would settle all of it** is one evening: the same oil in both solvents, at three
dilutions, plus ten repeats with the jar left alone and ten with it re-seated. The first arm answers
whether it goes clear. The second answers whether dilution-invariance survives. The third compares
against two numbers we already have — and it is the one that could change what we work on next, because
the re-seating scatter we currently blame on the sample holder was itself measured through a turbid
liquid, and nobody has yet checked what it becomes in a clear one.

**Nothing changes today.** The instrument keeps isopropanol, and the case above is a case for a
measurement, not for a substitution.

> ⭐ **The measurement is now scheduled.** The solvent and its vessels arrive on 20 August 2026, and
> `SPEC_capture_quality.md` §16.12.7e sets out the evening: a blank first, then clarity, then dilution, then
> the re-seat comparison, with what each result would mean written down before the data.
>
> ⛔ **One thing in §6.6 below governs it, and it is not an optical argument.** The lamp is a 220-volt unit
> directly beneath the sample, so any vessel change is argued on leak risk first: a one-piece vial with a
> lined cap qualifies, a cup closed by a workshop-milled lid does not. And **polypropylene cannot be the
> cuvette at all** — §6.6 rejects it as hazy, which is to say it would manufacture the very scattering
> pedestal chapter 5 is about, and feed it back through the beam. The PP cups are for mixing and storage;
> the light must not pass through them.

### 4.9 ⭐⭐ The fifth ligand — and why the emulsion may be a FEATURE  *(2026-08-21)*

§4.8 asked what a hydrocarbon would **remove**. The white-spirit evening then ran, and its results are
`SPEC_capture_quality.md` §16.12.7f. This section answers the question nobody had asked: **what does the
emulsion give us that a true solution would take away?**

#### What a "coordinating solvent" means, in one paragraph

The pigment carries a **magnesium ion at the centre of a flat ring**, held by four nitrogens (§3.2). Four
bonds is one or two short of what magnesium prefers, so it keeps an **open site pointing straight out of the
ring face**, perpendicular to it. Any molecule with a spare lone pair of electrons can donate into that site,
and an alcohol's oxygen does it well. **Steric hindrance** is simply how much bulk sits around that oxygen and
gets in the way as it approaches the flat face:

| solvent | what the oxygen carries | the fifth site |
|---|---|---|
| **methanol** | one small CH₃ | binds readily — the least hindered of the series |
| **ethanol** | CH₂CH₃ | between the two |
| **2-propanol** *(in use)* | CH(CH₃)₂ — two methyls branching off the very carbon next to the oxygen | **binds, but more weakly**: that bulk collides with the ring face on approach |
| **de-aromatised white spirit** | no lone pair anywhere | ⛔ **cannot bind at all** |

⛔ **That last row is the hydrocarbon's hidden cost.** With no solvent ligand available, the magnesium can
take its fifth ligand from a **neighbouring pigment molecule** instead — a dimer, with shifted and broadened
bands. Dimerisation is an *equilibrium*, so the spectrum then depends on concentration, and a metric built on
dilution-invariance cannot survive that. §4.8 gives four reasons it should not happen here: micromolar
concentrations against a millimolar phenomenon; roughly ten thousand ester carbonyls per pigment molecule
supplied by the dissolved oil, and any ligand in excess breaks the aggregates; up to a third of the pool being
magnesium-free protopheophytin already; and hardware-shop solvent carrying water, which is itself a ligand.
⚠ **They are arguments, not measurements.**

#### ⭐⭐ Structural invariance against conditional invariance

![**Figure 6** — the mechanism, drawn. **A:** in isopropanol the pigment is lipophilic and sits *inside* the oil droplets. Diluting changes how many droplets stand in the beam, never the concentration inside one — so the magnified view is identical at both dilutions, and every concentration-dependent process is frozen at one operating point. **B:** in white spirit the oil dissolves and the pigment's real concentration *is* the nominal one; halve it and the molecules sit ≈ 1.26× further apart, so aggregation and the dimer of the table above become live variables. ⚠ A mechanism drawing, not measured data.](figures/solvent_dilution_invariance.svg)

The point is geometric, and it is easier to see than to say. In the emulsion the pigment is **lipophilic and
therefore inside the oil droplets**, at whatever concentration the oil itself has. Diluting the preparation
changes **how many droplets sit in the beam** — never the concentration inside one of them. Every process that
depends on concentration is therefore **frozen at a single operating point** and cannot respond to dilution at
all. In a true solution the pigment's real concentration **is** the nominal one; halve it and the molecules sit
about 1.26× further apart — the cube root of two — and those same processes become live variables.

⇒ ⭐ **In isopropanol, dilution-invariance is *structural*. In a hydrocarbon it becomes *conditional*** —
conditional on the pigment not interacting with itself. `DOC_capture_fidelity.md` §3.12 measures the
isopropanol case at **± 0.35 % across every dilution simulated, against an 8.7 % run-to-run spread.** The
hydrocarbon case is **untested**: arm B of §16.12.7e — three dilutions in both solvents — has not run, and it
is the arm that can refuse the solvent outright.

⛔ **None of this says the emulsion reads the TRUE spectrum. It does not.** The pigment is packaged rather
than dispersed, and Beer–Lambert assumes dispersed (§2.2); the reading is wrong. What matters is that it is
wrong *consistently*: **constant-but-wrong is exactly what a ratio metric survives, and variable-but-right is
not.**

#### ⭐ The positive case for isopropanol, which had never been written down

§4.6 decides the solvent by **elimination** — every alternative fails on a named, checkable ground. That table
is still correct and nothing here revises it. But it leaves the impression that isopropanol is merely what
remains once the better options are struck out, and after the white-spirit evening that is no longer the whole
picture:

| | |
|---|---|
| **Safety** | non-toxic enough for a miller's shed. Decisive on its own, and it needs no physics |
| **Solvency at our working concentration** | marginal — but it holds more oil at 1.2 % v/v than the shorter alcohols do (§4.7) |
| **Ligand** | bulkier than methanol, but it coordinates the magnesium well enough to keep the pigment monomeric. The failure mode of the hydrocarbon row never arises |
| **⭐ The emulsion itself** | pins the pigment's *local* concentration, which is what makes dilution-invariance structural rather than something to be re-measured after every recipe change |
| **The threshold** | `T = 18.6` and the 12–22 verdict domain exist on this route and nowhere else. `Q%` shifted **+6.71** and **+2.09** between the two solvents — by different amounts per oil — so nothing carries across (§16.12.7f) |

⛔ **And what it costs, stated as plainly.** Worse fill-to-fill repeatability — the entire settling apparatus
of `SPEC_settled_measurement.md` exists to fight scatter that a true solution would not have produced — the
**+0.44 / +0.80** first-to-second-pour term of §36.2, which collapsed to **−0.166** in white spirit, and
absorbances that are wrong in absolute terms.

⚠ **"Better" here means better on the axes that have been measured, not proven best.** §4.8's case for the
hydrocarbon is **not withdrawn**, and arm B remains the one cheap experiment that could reorder all of this.

#### ⚠ One candidate this reopens, weakly: ethanol

Recorded so that it is not re-derived from scratch; it is **not a proposal and creates no work item.**
**Ethanol** is the only member of the series that is both **food-grade** and a **less hindered ligand** than
isopropanol. ⛔ It is *worse* on the axis §4.5 says matters most — more polar than isopropanol, so poorer at
dissolving triglyceride, and it would coarsen the emulsion rather than clear it. Its real interest is
indirect: §4.7's standard methods use **ethanol/isooctane** and **ethanol/heptane** *mixtures*, which suggests
that if the solvent question is ever genuinely reopened the answer is a **mixture** — an alcohol for the
ligand, a hydrocarbon for the solvency — rather than any single solvent at either end of the series.
⛔ Methanol is not a candidate at any dilution: acutely toxic and skin-absorbed.

⇒ ⭐ **And there is a row this table does not have.** Every entry above treats the axis as *polarity* —
alcohols coordinate, hydrocarbons do not. A **triglyceride** is nonpolar *and* carries ester carbonyls,
so it can do both. §4.10.

## ⭐⭐⭐ 4A. SUNFLOWER IS THE SOLVENT  *(Edwin's decision, 2026-08-25)*

§4.9's table asked which solvent coordinates the magnesium. §4.10 found the row that table did not have.
This chapter records what happened next: **sunflower oil is the solvent the instrument will use.**

⛔ **CHOSEN, NOT MIGRATED.** Isopropanol is still the shipping recipe and the archive is still 88 %
isopropanol. What follows is the case, and §4A.4 is the honest list of what the decision does not settle.

### ⭐⭐ 4A.1 The result that makes the decision safe — the threshold transfers unchanged

A solvent migration normally means a full re-calibration: §16.12.7g's own warning is that *"every
threshold is isopropanol-fitted."* For the metric being retired that is exactly right — the **same
Lugitsch oil** reads `Q%` **13.5–15.5** in isopropanol, **16.2–16.7** in sunflower and **20.6–20.8** in
white spirit. No single threshold survives that.

⭐ **The verdict metric does not have that problem.** `Rv` at its provisional `T = 52`:

| solvent | green, lowest | brown, highest | **margin** | errors at `T = 52` |
|---|--:|--:|--:|--:|
| isopropanol (n = 28) | 98.4 | 46.4 | **+52.0** | **0** |
| **sunflower (n = 12)** | **113.4** | **45.5** | **+67.9** | **0** |
| white spirit (n = 4) | 103.1 | 36.9 | +66.2 | **0** |

⇒ **The threshold does not move, and the margin is WIDEST in sunflower** — 31 % wider than in the
solvent it replaces. The metric and the solvent were chosen independently and turn out to fit each other:
`Rv` is what makes a solvent change cheap, and sunflower is where `Rv` performs best.

### ⭐⭐ 4A.2 Why sunflower wins — six measured advantages

| | |
|---|---|
| **1 · it dissolves the oil** | n = 1.473 against the oil's 1.47. Isopropanol is 1.377 and only **emulsifies** it. A true solution, not a dispersion |
| **2 · ⭐ the 624 nm band becomes a WHOLE PEAK** | maximum at **623–625 nm falling 81–99 %** by 633 nm. In isopropanol the same window merely rises to 629–630 and plateaus (4–14 %) — there is no resolved band to measure at all |
| **3 · the bands are 2–6× better localised** | second-derivative dip positions **623.8 ± 0.6** and **568.5 ± 0.3 nm**, against isopropanol's 626.0 ± 1.5 and 570.1 ± 1.8 |
| **4 · the margin is wider** | §4A.1, and green-class scatter falls from sd 8.1 to **4.9** |
| **5 · food-safe** | white spirit is not, at any concentration (§6.6). This is what rules the hydrocarbon out of a product regardless of how well it performs |
| **6 · visible to the naked eye** | the difference between two pumpkin oils, seen at the bench without an instrument (`DOC_solvent_and_hue.md` §3) |

⭐ **Advantage 2 is the one that matters most**, and it is the reason the metric exists. `Rv` reads a 5 nm
band at 624 nm. In an emulsion that band is broadened and shifted until there is no peak inside the
measured range; in an index-matched solvent it is a clean maximum with both flanks. **The solvent did not
improve the measurement of a band — it produced the band.**

### 4A.3 Why the index match does that — and what it says about the pigment

§4.10 below sets out the chemistry: a triglyceride is nonpolar **and** carries three ester carbonyls per
molecule, so it occupies the corner §4.9's polarity axis has no room for — a true solution *and* a ligand
in vast excess.

The optics follow. Matching n to 1.47 removes droplet scattering, which is why the pedestal collapses.
But the band **position** also moves — 629–630 nm in the emulsion against 623–625 nm in solution — and a
band that is both **broadened and red-shifted** in the dispersed phase is the signature of **aggregation**:
inside a droplet the pigment is at neat-oil concentration, not micromolar, and that is the regime where a
chromophore interacts with itself. §16.12.7g argues this from a 13.6× dose-free area difference; the peak
shift is a second, independent line of evidence for the same mechanism.

⚠ The alternative is not excluded: in isopropanol the band may be so weak that the rise toward 630 nm
belongs to a *background* rather than to the band, in which case there is no shift to explain.

### ⛔ 4A.4 What the decision does NOT settle

- ⛔ **The E3 gate has not run in full.** §16.12.7g requires four fills — green and brown oil × isopropanol
  and sunflower — reported as `area(624)/area(Soret)`. Two arms exist; the full design does not.
- ⛔ **n is small and narrow.** Twelve sunflower runs against 88 labelled isopropanol ones, and only **two
  oils** (Lugitsch, Billa Clever) have been measured in sunflower *and* another solvent.
- ⛔⛔ **The preparation stratifies, and it is worse in a viscous solvent.** The second half of a prepared
  sample carries **15–45 % more absorber** than the first: pigment-rich material settles in the mixing
  vessel over ~2 h. `Rv` absorbs it (a 40–45 % dose swing moves it < 0.8 %), but any level-reading quantity
  will not. ⇒ mix immediately before pouring, and record which half was poured.
- ⛔ **The bottle is a variable.** Old versus fresh sunflower moved `Q%` by 2.4 units on one oil while
  leaving `Rv` flat. Record the bottle.
- ⛔ **Sunflower may be the proof of concept, not the destination.** `DOC_solvent_and_hue.md` §5 argues
  **MCT oil** is better where sunflower is weak — thinner, cleaner, and colourless. The case above is a
  case for *index matching*; sunflower is the cheapest available instance of it.
- ⚠ **The turbid oil is still the problem.** In sunflower the worst oil still scatters 15 % run-to-run
  (`Rv` sd 5.68) against 0.72 for the best. The solvent did not fix that; the preparation arm might.

### 4A.5 What must happen before the migration

1. **Record the solvent and the bottle in every report.** The `METADATA` phase is empty today, and the
   solvent is now the largest single term in the metric being retired.
2. **Run the preparation arm** — one turbid oil, four ways (shaken/immediate, shaken/fixed wait, filtered,
   sonicated) — to decide whether particulate removal is safe. ⭐ The readout: if turbidity falls and the
   pigment bands hold, the particulates carry no pigment and filtration is safe.
3. **Re-run the pre-registered test in sunflower**, not only in isopropanol, so the frozen `T = 52` is
   validated in the solvent it will actually run in.

---

### ⭐⭐ 4.10 SUNFLOWER OIL — the row §4.9's table does not have  *(2026-08-22 evening, measured 2026-08-24)*

§4.9's ligand table runs from methanol to de-aromatised white spirit and treats the axis as **polarity**:
alcohols coordinate the magnesium, hydrocarbons cannot. **Sunflower oil is not on that axis.** It is a
triglyceride — nonpolar like the hydrocarbon, but carrying **three ester carbonyls per molecule**, and a
carbonyl oxygen has lone pairs.

| solvent | polarity | fifth-ligand donor? | dissolves the oil? |
|---|---|---|---|
| 2-propanol *(shipping)* | polar | yes — hindered, but yes | ⛔ no: emulsion (§4.2) |
| de-aromatised white spirit | nonpolar | ⛔ **none** | ✅ yes |
| **sunflower oil** | **nonpolar** | ✅ **yes — ester C=O** | ✅ **yes** |

⇒ ⭐ **Sunflower occupies the corner §4.9 could not offer: a true solution AND a ligand in vast excess.**
§4.9 itself supplies the count — *"roughly ten thousand ester carbonyls per pigment molecule supplied by
the dissolved oil, and any ligand in excess breaks the aggregates"* — but it makes that argument about
*dissolved pumpkin oil inside white spirit*. In sunflower the entire solvent is that ligand.

#### What sunflower buys — six things, each with its number

⭐ **1. The oil actually dissolves.** n = 1.473 against the oil's 1.47, so the refractive-index mismatch
that drives §4.2's emulsion and §5's pedestal is essentially gone. Isopropanol is 1.377 and only
emulsifies.

⭐ **2 – 5** are measured, and are the table below: the **baseline**, the **settling**, the **624 nm
band** and the **568 nm band**.

⭐ **6. It is food-safe.** §4.8's de-aromatised white spirit shows every one of these effects more
strongly and can never enter a product at any concentration; §4.6's decision table rules solvents out on
exactly this ground. Sunflower oil passes it.

⇒ And one that is commercial rather than physical: **the difference between the two oils is visible to
the naked eye** in sunflower (§3.7's dichromatism, and Figure 7 below). A device whose answer a miller
can confirm by looking is a different proposition from one that must be believed. `DOC_solvent_and_hue.md`
§3 records a four-sigma separation by eye, with the spectrometer predicting one of the two hues to 2.1°.

`DOC_solvent_and_hue.md` is the full account; the numbers that bear on this section:

| | sunflower | isopropanol archive |
|---|---|---|
| **baseline `A_valley`** | **0.018** — 2nd lowest of 116 runs | typical 0.09, worst 0.28 |
| ⭐ **settling** | `SETTLED_IMMEDIATE` at 106 s, `Q%` span **0.03** over the whole run | fill-to-fill benchmark 0.38 |
| **624 nm band**, dose-free `area(624)/area(Soret)` | **0.01808 ± 0.00561** (n = 3) | **0.00133 ± 0.00100** (n = 72) |
| **568 nm band** (the band the verdict reads) | ~2× — §12.6 of `SPEC_metric_research.md`, on 110 fills | |

**13.6×, with no overlap** — sunflower's weakest fill is 3.2× isopropanol's strongest. And the
green/brown **ordering survives**: green above brown in isopropanol (d = +0.96, n = 72), in sunflower and
in white spirit alike, with the gap widening from 0.0009 to 0.0095.

![**Figure 7** — the two oils in sunflower oil, and the same two in the report's own rendering. The difference that the archive's isopropanol runs never showed by eye.](figures/solvent_hue_photo.png)

#### ⭐⭐ The mechanism this suggests — and where §4.9's own reasoning stops short

§4.9 argues the emulsion is a **feature**: the pigment is lipophilic, so it sits *inside* the droplets at
whatever concentration the neat oil has, and diluting changes only how many droplets stand in the beam.
That is what makes dilution-invariance **structural**. Nothing here revises it.

⛔ **But it has a consequence §4.9 does not follow through.** §4.9 dismisses aggregation in the
hydrocarbon on the ground that *"micromolar concentrations [face] a millimolar phenomenon"*. That
argument is about the **nominal** concentration of a true solution. **Inside a droplet the concentration
is not micromolar — it is that of neat oil**, which is precisely the regime where aggregation lives.

⇒ The same packaging that pins the local concentration also **pins it at the value where the pigment can
interact with itself.** An aggregated or self-coordinated pigment has a weakened, broadened Qy band —
which is exactly the 13.6× deficit measured above, and exactly why it appears in the **narrow red band**
and not in the broad Soret.

⚠ **This is an argument, not a measurement.** `SPEC_color_retrieval.md` §7.16.4a establishes only the
negative half — that no *optical* explanation survives, because a 16.6× dose-free **area** difference
cannot be convolution, and every scattering candidate would damage the Soret more than the red band.
What remains is a change in the pigment's own state. §4.9's ligand chemistry is the natural candidate;
it has not been shown.

⇒ ⭐ **It makes arm B of §16.12.7e considerably more interesting than a dilution check.** If the deficit
is aggregation inside droplets, then in **isopropanol** the `624/Soret` ratio must be *independent of
nominal dilution* — the droplet interior does not change — while in **sunflower** it should stay flat
only until the true concentration climbs into the aggregating regime. Three dilutions in both solvents
tests the mechanism, not merely the invariance.

#### ⚠ 4.10.1 What this does NOT settle

- ⛔ **`Q%` is not solvent-portable.** §16.12.7f measured **+6.71** and **+2.09** — *different per oil*.
  The ordering result above is the `624/Soret` ratio, a **different quantity**; it neither contradicts
  that nor rescues it, and §4.9's table already records that `T = 18.6` exists on the isopropanol route
  and nowhere else.
- ⛔ **n = 3, with one brown fill.**
- ⚠ Sunflower is viscous to dose and leaves a film to clean; §5 of `DOC_solvent_and_hue.md` argues **MCT
  oil** (C8/C10) is better on exactly those counts, and is the same chemistry — a triglyceride, so the
  ester-carbonyl ligand argument carries across unchanged.
- ⇒ ⏸ **The gate is E3** (`SPEC_color_retrieval.md` §7.16.5): four fills, one evening, green and brown
  oil × isopropanol and sunflower. Nothing above justifies a migration before it runs.

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

⭐ **And it is why the shipped metric is not a ratio of two bands.** `Q%` puts the two pigment windows into
a **difference** — $A_{Q} - A_{valley}$ — so a flat pedestal subtracts out instead of dragging a quotient
toward 1, and only then divides by the Soret to remove the multiplicative half. ⚠ **The hole is narrowed,
not closed**: real Mie scattering has spectral *slope* (§5.2), and a slope does not cancel between two
windows at different wavelengths. What this section measures is still the largest single nuisance in the
jar; what changed is which part of it survives the arithmetic.

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
   distinction between polarity and solvency matters — but **this route is closed for this instrument**
   (§4.6, §6.6): every solvent that dissolves the oil properly either carries an unacceptable hazard
   classification or attacks the vessel, and the vessel sits above a mains-voltage lamp.
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
| 2-butanol | ⚠ **not computed** | likely **closer to PS** than 1-butanol — see below; not pursued (§4.6) |
| isooctane | 1.27 | outside |
| **2-propanol** | **1.29** | outside — safe |
| 1-propanol | 1.33 | outside |
| ethanol | 1.49 | comfortably outside |
| water | 3.23 | inert |

> ⚠ **2-butanol's RED is deliberately left blank rather than estimated.** Computing it needs the same source's
> polystyrene parameters, and a value derived from a different source would not be comparable with the rows
> above. **But the direction is predictable and it is the wrong one:** 2-butanol is a *secondary* alcohol, so
> its hydrogen-bonding term δH is **lower** than 1-butanol's — which moves it **toward** polystyrene in Hansen
> space, i.e. toward the swelling boundary that heptane sits on at 1.10. A resin-compatibility guide
> independently rates 2-butanol against PS only as *"moderate–good, with caution"*, against 1-butanol's clean
> "safe at 20 °C". **Two independent hints in the same direction ⇒ the overnight soak test
> (`SPEC_capture_quality.md` §16.12.7 item b) is a gate, not a precaution.**


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
vessel with a matching clear lid is not something one simply buys in glass. The usual answer would be a
lid with an aperture carrying a clamped **fluorinated ethylene propylene (FEP)** film: better than
95 % transmission across the visible, under 2 % haze, chemically immune to everything discussed here,
and clamped rather than glued, since the non-stick nature that makes it solvent-proof also means
nothing adheres to it.

### 6.6 ✅ The decision: the polystyrene vessel stays — and a safety constraint decides it

**The instrument keeps its existing sealed polystyrene jar.** Two reasons, and the second is the one
that settles it.

**First, nothing better is available off the shelf.** A one-piece vessel with an integral transparent
lid does exist in food packaging — hinged sauce cups, for instance — but those are moulded in
**polypropylene**, which is semi-crystalline and **hazy**. Haze is wide-angle scatter: precisely the
pedestal chapter 5 is about, fed straight back into the beam. They are also tapered for stacking, with
no flat reference surface, which is the opposite of what a repeatable optical seating needs. Disposable
spectrophotometer cuvettes are made of polystyrene or PMMA exactly because those are optically clear.

**Second — and this is decisive — the vessel sits above mains electricity.** The lamp is a **220 V**
unit housed in the **lower cone**, directly beneath the sample, because the beam runs top-down. **Any
leak runs down into it.**

> **⇒ Vessel integrity is a safety property of this instrument, not a measurement property.** A milled
> glass lid, a clamped polymer window, or any workshop adaptation is a *fabricated seal of unknown
> reliability sitting over mains voltage* — and the more aggressive the solvent it is asked to contain,
> the worse the consequence of a failure. **Any future vessel change must be argued on leak risk first
> and optics second.** The sealed, single-piece, known-good jar in use today is doing more work than it
> is usually given credit for.

This is also what closes the acetone option of §4.6: the chemistry is attractive, but it requires a new
vessel, and every available new vessel is either optically worse or a hand-made seal over a 220 V lamp.

**The change that would dissolve the constraint** is a rebuild to **side illumination** — a horizontal
beam, with the lamp no longer beneath the sample. That would also permit standard cuvettes, fixing path
length and seating at the same time. It is a genuine option and a real redesign of the instrument; it is
not currently planned.

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
