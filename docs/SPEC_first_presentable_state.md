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
| 1 | ⚠ No-op version bump, **then** Soret trim 440–460 → 448–460 + re-sign | 1 | desk | the plugin publish path works |
| 2 | Opaque-oil test — measure `f` | 1 | bench | is the aperture worth building? |
| 3 | Slide-in sample holder — design, print, fit | 1 | build | wall-bypass light removed, tilt controlled |
| 4 | ⛔ Gates **G1 + G2**, settle the capillary recipe | 2 | bench | is the capillary usable at all? |
| 5 | Re-run **green-vs-brown** and **green-vs-green** | 2 | bench | ⭐ **GO / NO-GO: is green-vs-green *d* ≥ 3?** |
| 6 | Derive and **write down** the thresholds | 1 | desk | ⭐ **THRESHOLDS FROZEN** |
| 7 | P3a — 8 oils, 24 fills | 2 | bench | out-of-sample behaviour |
| 8 | Blind judging, 2 judges | 1 | people | agreement with expert opinion |
| 9 | Analysis + write-up | 1 | desk | ⭐ **FIRST PRESENTABLE STATE** |

**At 5 sessions/week ⇒ ~2.5 weeks.** ⚠ **13–15 days** if either tail item (§4) fights back.

⚠ Everything is **sequential**, and not by preference: the aperture changes the optical path, so the capillary
runs must follow it; the thresholds come from the capillary corpus, so they must be frozen before the
validation sees any oil.

## 3 · The three gates, in order

**⭐ GO / NO-GO — after step 5.** Green-vs-brown is already met (*d* ≈ 7.5, non-overlapping). The open half is
**green-vs-green: *d* ≈ 1.34 today, ≳ 3 needed, ~3.5–5 projected** (`SPEC_capture_quality.md` §16.26.13).
⛔ **If it comes back at *d* ≈ 2, the milestone does not happen** — you are back in research, and the parked
range-extension track (§6) stops being optional.

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
| oils unavailable | eight shop-available oils | ▶ start the shopping in parallel with step 1 — it is the only item that depends on anyone else |

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
- [ ] G1 and G2 passed; capillary recipe settled and written down
- [ ] green-vs-brown re-confirmed; **green-vs-green measured** with *d* reported
- [ ] thresholds derived, **dated and written down**, on the held oils only
- [ ] 8 oils measured out-of-sample, 24 fills, fresh per fill
- [ ] both judges' scores **sealed before** any instrument output was shown
- [ ] one-page write-up stating the claim **and its limits** (§5)
