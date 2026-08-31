# SPEC — FIRST PRESENTABLE STATE *(schedule; agreed with Edwin 2026-08-06)*

> **Diagram:** [`first_presentable_state.svg`](../../spectracs-docs/first_presentable_state.svg) — the Gantt.
> Generated from [`first_presentable_state.puml`](../../spectracs-docs/first_presentable_state.puml);
> regenerate with `java -jar plantuml.jar -tsvg first_presentable_state.puml`.
> **Backlog:** the same items appear in [`ROADMAP.md`](../../spectracs-docs/ROADMAP.md) as
> *NEXT TASK / PRIO 1 / PRIO 2 / PRIO 3a*. This document is the **schedule**; that one is the backlog.

## 1 · What this milestone is

**The point at which the metric stops moving.**

Today the metric is still in motion — a Soret-window change is adopted but unshipped, a reduction-band change
is in but unproven, and the thresholds have never been derived on the configuration they will ship with.
Nothing can be presented while that is true, because any number quoted would be superseded by the next commit.

⇒ **First Presentable State = the metric and its thresholds are FROZEN, the capability is measured rather than
projected, and the whole thing has survived contact with eight oils it had never seen.**

⚠ **It is NOT the end of validation.** It is the end of the *research state*. See §5 for the distinction, which
matters when talking to a lab owner.

## 2 · The schedule

**12 working days**, the upper end of Edwin's 10–12 estimate — a plan should not be built on the optimistic end.

| # | step | days | kind | gate it clears |
|---|---|---|---|---|
| 1 | ✅ **Soret trim 440–460 → 448–460 DONE 2026-08-10** (`SPEC_soret_448_trim.md`), thresholds re-derived (T 6.8 / 8.3). ⚠ **No re-sign was needed or possible** — `DevSpectralPlugin` fails the publish lint (four sibling imports), so the bench loads the built-in. ⛔ The **no-op version bump + publish rehearsal is still owed** and must use `PumpkinOilPlugin`, the only plugin that passes the lint | 1 | desk | the plugin publish path works |
| 2 | Opaque-oil test — measure `f` | 1 | bench | is the aperture worth building? |
| 3 | Slide-in sample holder — design, print, fit | 1 | build | wall-bypass light removed, tilt controlled |
| 3b | ⭐ **DN guard** — record `min(S)`, warn out of window (§16.23.8) | *(parallel)* | desk | a bad fill is caught **at capture**, not in analysis |
| 4 | ⛔ Gates **G1 + G2**, settle the capillary recipe | 2 | bench | is the capillary usable at all? |
| 5 | Re-run **green-vs-brown** and **green-vs-green** | 2 | bench | ⭐ **GO / NO-GO: is green-vs-green *d* ≥ 3?** |
| 6 | Derive and **write down** the thresholds | 1 | desk | ⭐ **THRESHOLDS FROZEN** |
| 7 | P3a — **9 oils**, 27 fills | 2 | bench | out-of-sample behaviour |
| 8 | Blind judging, 2 judges | 1 | people | agreement with expert opinion |
| 9 | Analysis + write-up | 1 | desk | ⭐ **FIRST PRESENTABLE STATE** |
| ‖ | ⚠ **Oil shopping — 9 oils for P3a** | *(parallel, lead time)* | logistics | ⛔ in hand **before day 9 (Wed 19 Aug)** |

**Start Friday 7 August 2026 ⇒ FIRST PRESENTABLE STATE on Monday 24 August**, at 5 sessions/week.
⚠ **13–15 days ⇒ 26–28 August** if either tail item (§4) fights back.

⭐ **Step 3b costs no schedule day** — it is desk work running in parallel with the aperture print, which has
dead time. ⚠ But it must land **before** step 4: the guard is two-sided (record `min(S)` per capture, warn when
it leaves the 16 DN floor / 20–40 DN target band, propose the correction — warns, never blocks), and its whole
value is telling you a fill was out of range **at capture** rather than in analysis three days later. ⇒ It also
consumes G2's finding directly: the capillary's ±10 % volume band is exactly what pushes a fill out of the DN
window.

⚠ Everything else is **sequential**, and not by preference: the aperture changes the optical path, so the capillary
runs must follow it; the thresholds come from the capillary corpus, so they must be frozen before the
validation sees any oil.

## 3 · The three gates, in order

**⭐ GO / NO-GO — after step 5.** Green-vs-brown is already met (*d* ≈ 7.5, non-overlapping). The open half is
**green-vs-green: *d* ≈ 1.34 today, ≳ 3 needed, ~3.5–5 projected** (`SPEC_capture_quality.md` §16.26.13).
⛔ **If it comes back at *d* ≈ 2, the milestone does not happen** — you are back in research, and the parked
range-extension track (§6) stops being optional.

> ⭐⭐⭐ **THE OPEN HALF NOW HAS STRONG EVIDENCE — 2026-09-01, and it did not come from this plan.** The
> `20280831_suite` (`SPEC_metric_research.md` §16.15.7) is every fill confirmed same-jar AND 6-min cold-box —
> one method, one recipe, no protocol term left in the comparison. Scored on **`Rv`**, using the conservative
> **pooled σ_fill of 3.91** rather than each pair's own tiny-sample sd:
>
> | green vs green | gap | *d* at σ_fill 3.91 | *d* on the pair's own sd |
> |---|---|---|---|
> | Ja Natuerlich vs Lugitsch | 15.40 | **3.94** | 4.51 |
> | Lugitsch vs Steirerkraft | 23.98 | **6.13** | 6.92 |
> | Ja Natuerlich vs Steirerkraft | 39.38 | **10.07** | 38.97 |
>
> **All three clear *d* ≥ 3**, and green-vs-brown in the same corpus runs *d* 14–24. ⇒ on this evidence the
> GO/NO-GO is expected to pass, and the parked range-extension track (§6) stays optional.
>
> ⛔⛔ **THIS IS NOT THE STEP-5 VALIDATION AND MUST NOT BE COUNTED AS IT.** Step 5 is a run against **frozen
> thresholds** on a corpus the freeze has not seen; this is a different metric (`Rv`, not the one the 1.34
> was measured on) scored on data already in hand. It says the gate is *likely* to pass — it does not pass it.
> ⚠ And two of the four oils carry **2 fills**, so their σ has 1 df; the 3.91 column is there because the
> pair's-own-sd column cannot be trusted at that n.
> ⚠ Every instrument caveat of `SPEC_capture_quality.md` §16.40 applies underneath: the fill-to-fill
> differences are 1–3 camera counts, ~5 Rv of the scatter may be the lamp's red tilt, and the `pow2.2` decode
> the DN framing rests on is unverified.

**⭐ THRESHOLDS FROZEN — after step 6.** Derived on the capillary corpus, from the **oils already held**
(Kiendler, Steirerkraft, S-Budget). ⛔ **Written down with a date, and never re-fitted afterwards.** Re-fitting
them once P3a has seen an oil converts a validation into a demonstration, retroactively.

**⭐ FIRST PRESENTABLE STATE — after step 9.**

## 4 · Risks, and only two are real

| risk | why | mitigation |
|---|---|---|
| ⚠⚠ **the publish path** | `publish → assign → load` has **never been run end to end**. The Soret trim is one constant; getting a re-signed plugin onto the bench is the unknown | ▶ **no-op version bump FIRST**, inside day 1, so a failure there is not tangled with a metric change |
| ⚠ **the print fit** | two apertures at the jar's **inner** diameter; 3D-printed fit parts iterate | budget a second print; the `f` test (step 2) tells you first whether it is worth any prints at all |
| G1 fails (heparinised capillaries) | heparin is insoluble in IPA and would add **scatter** — to the one system whose open problem is a scattering pedestal | ⛔ **run G1 before committing to the schedule**; a failure is a re-sourcing detour, not an evening |
| ⚠ **oils unavailable** | eight shop-available oils, and **the only item on the path that depends on anyone but Edwin** | ▶ **start in week 1** — 8 working days of lead time to day 9. ⚠ If a tier cannot be filled, say so early: **2 browns is the minimum** that lets the class claim rest on more than one bottle (§2.2) |

⚠ **Not a risk, but worth stating:** the ageing rule (§16.11.16 — a 24 h-aged fill reads as a *browner oil* and
misclassified 3 of 3 runs) caps how many fills fit in a day, because each must be measured fresh. That is
already inside the day counts for steps 5 and 7.

## 5 · What the milestone licenses — and what it does not

✅ **Sayable:** *"Eight oils, two independent experts scoring blind, thresholds frozen in advance and never seen
by these oils. The instrument agrees with expert judgement, separates roasted from unroasted with no overlap,
and ranks within the green class."*

⛔ **Not sayable:**

| claim | why not | what earns it |
|---|---|---|
| *"it measures roast level"* | ⚠ **no objective ground truth** — shop-bought oils carry no mill roast record. P3a validates agreement with *expert judgement* | PRIO 3, the full study, with roast level from the mill |
| *"it generalises"* | n = 8, one region, one season | PRIO 3's wider panel |
| *"it is validated"* | post-research ≠ validated. The method is settled; the claim has not met ground truth | PRIO 3 |

⇒ **You may legitimately build product in that gap. You may not make the claim in it.**

## 5a · ⚠ Two statistical facts that shape P3a

**1 · The panel is 3 non-premium vs 4 premium, not 2 vs 4 — and that is not padding.** A rank test's p-value
has a floor set by the number of possible orderings, reached only on a *perfect* separation:

| design | best possible p | |
|---|---|---|
| 2 vs 4 *(originally proposed)* | 0.067 | ⛔ **cannot reach p < 0.05 at all** |
| 3 vs 3 | 0.050 | ⛔ on the boundary |
| ⭐ **3 vs 4** *(adopted)* | ⭐ **0.029** | reachable |

⇒ **One extra bottle buys the claim.** ⚠ Without it, the observation Edwin most wants — *a non-premium green
showing up as non-premium* — would be suggestive but **not defensible**.

⚠ **The asymmetry matters:** a **positive** result is clean; a **null** result is uninformative, because a
failure to separate cannot distinguish "the metric failed" from "premium doesn't track roast".

**2 · Green-vs-green is a PROBABILISTIC call and must be presented as one.** Error per side for a single
sample, at the optimal cut:

| case | *d* | error |
|---|---|---|
| **green vs brown**, measured | 7.50 | **0.01 %** — effectively deterministic |
| green vs green, projected | 3.50–5.00 | 0.6 – 4.0 % |
| green vs green, today | 1.34 | 25.1 % |
| ⭐ green vs green, `Rv` on the `20280831_suite`, 2026-09-01 | **3.94 – 10.07** | **0.6 % – ~0** |

⇒ ⭐ **The brown verdict may stay a BADGE; a within-green result must be a RANKING WITH A CONFIDENCE.**
Presenting them identically overclaims the weaker one by three orders of magnitude. ▶ And report any
within-green gap as *"X against a within-oil σ of Y"*, never as a bare ordering.

## 6 · The parked track — deliberately off the critical path

The **calibration extension + 660–680 nm quiet-window test** (`SPEC_metric_research.md` §7.14.5) is cheap,
independent, and genuinely valuable — it is the precondition five closed analytical routes were waiting on.

⛔ **But its result must not enter the shipped metric before the freeze.** It could reopen the far anchor, free
the Qy band, and change the metric's *form* — which is exactly what step 6 forbids.

⇒ **You cannot be post-research and still exploring the range.** Run it in parallel, bank the answer, and adopt
it — if it pays — at a **future version boundary**, after PRIO 3.

## 7 · Definition of done

- [ ] plugin published, assigned and loaded on the bench with the trimmed window
- [ ] `f` measured; aperture built or explicitly declined on the evidence
- [ ] DN guard implemented and live before the first capillary run
- [ ] G1 and G2 passed; capillary recipe settled and written down
- [ ] green-vs-brown re-confirmed; **green-vs-green measured** with *d* reported
- [ ] thresholds derived, **dated and written down**, on the held oils only
- [ ] **9** oils bought (2 brown / **3** non-premium / 4 premium), **with their labels recorded at purchase**
- [ ] 9 oils measured out-of-sample, 27 fills, fresh per fill
- [ ] both judges' scores **sealed before** any instrument output was shown
- [ ] one-page write-up stating the claim **and its limits** (§5)
