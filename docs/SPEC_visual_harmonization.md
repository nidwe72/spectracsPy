# Spec — Visual Harmonization (spacing + color consolidation)

Status: **DRAFT / spec only — no implementation until explicitly requested.**
Scope: PySide6 desktop app. Goal: a consistent look throughout the app by (A) introducing a
spacing system and (B) consolidating colors into one source of truth and a Bootstrap-style
semantic palette.

---

## 1. Problem (current state, as found)

- Styling base is a **~380-line global QSS** in `spectracsMain.py` (a dark theme) + a tiny
  `ApplicationStyleLogicModule` singleton holding **4 `QColor`s** used only for custom painting
  (chart pens, Hough lines, scatter series).
- **Two disconnected color systems** that never share values: the singleton (QColor, for painting)
  and the QSS (hex literals). Result: two "brand greens" — `#3D7848` (singleton) vs `#33663d`
  (QSS buttons / logo / chart pens).
- **Borders are already consistent** (`1px solid #5A5A5A` throughout the QSS). Borders are *not*
  the problem.
- **Spacing has no system.** `setContentsMargins` values are ad hoc: `(0,0,0,0)`, `(1,1,0,0)`,
  `(0,5,5,5)`, `(-20,-10,-10,-10)`. **Zero `setSpacing` calls.** Negative margins are workarounds
  fighting Qt Charts' built-in padding. QSS uses `padding:` in only 4 places.
- Conclusion: the "dirty" feeling is **~80% spacing, ~20% duplicated color values** — not borders.

---

## 2. Decisions locked in (from discussion)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Brand green reconciliation | **`#3D7848` = primary**; `#33663d` demoted to pressed/hover shade |
| D2 | Color model | Bootstrap-style **semantic roles** |
| D3 | `info` hue | **Muted teal `#3D7878`** (NOT blue — stays in the green family) |
| D4 | `success` | **Reuse primary green** (fewer greens), not a separate swatch |
| D5 | Semantic variants | **Single accent each** for now; expand to bg/border/text triad later if needed |
| D6 | Single source of truth | All colors become named getters on `ApplicationStyleLogicModule`; QSS is **built from** those getters |

---

## 3. Spacing system (workstream A)

### 3.1 Token scale
One scale, referenced everywhere — never a raw pixel number again.

| Token | px | Use |
|-------|----|-----|
| `XS`  | 4  | tight inner gaps, icon-to-text |
| `S`   | 8  | sibling spacing, card inner padding |
| `M`   | 12 | page-level container margin |
| `L`   | 16 | section separation |
| `XL`  | 24 | major block separation / dialog gutters |

### 3.2 Application rules (the one consistent contract)
- **Page-level containers** → `setContentsMargins(M, M, M, M)`.
- **Sibling spacing** within a layout → `setSpacing(S)`.
- **Bordered card / panel** → inner padding `S` (via QSS `padding`, since the border lives in QSS).
- **Charts** → set the chart's own `chart.setMargins(QMargins(0,0,0,0))` /
  `setContentsMargins(0,0,0,0)`; **remove negative layout margins** entirely.
- No widget invents its own pixel value; it picks a token.

### 3.3 Where it lives
A `Metrics` accessor (sibling to `ApplicationStyleLogicModule`, same `style/` package) exposing the
five tokens as ints, so both Python layout calls and the QSS builder read the same numbers.

---

## 4. Color system (workstream B)

### 4.1 Semantic palette (6 roles)

| Role | Meaning in app | Hex | Note |
|------|----------------|-----|------|
| `primary`   | brand / main actions, active/selected | `#3D7848` | D1 |
| `primaryPressed` | pressed/hover of primary | `#33663d` | reuse old button green |
| `secondary` | info-like / neutral buttons | `#5A5A5A` | already in QSS |
| `success`   | good reading / pass | = `primary` | D4 |
| `info`      | hints, "expected detection" | `#3D7878` | teal, D3 |
| `warning`   | out-of-range, caution | `#C9942E` | muted amber |
| `danger`    | error / failed calibration | `#B0544E` | muted red |

### 4.2 Neutral ramp (name the grays already in the QSS)

| Getter | Hex | Current QSS use |
|--------|-----|-----------------|
| `getBackgroundColor` | `#191919` | main background |
| `getSurfaceColor`    | `#353535` | controls / panels |
| `getBorderColor`     | `#5A5A5A` | borders, unchecked indicators |
| `getTextColor`       | `#DDDDDD` | text |
| (existing) `getPrimaryTextColor` | `#FFFFFF` | on-primary text |
| (existing) `getSecondaryChartGridColor` | `rgb(30,30,30)` | chart grid |

### 4.3 Single source of truth
- Add the getters above to `ApplicationStyleLogicModule` (semantic roles + neutral ramp).
- **The global QSS string is generated from these getters** (f-string / template), so QSS and
  painted widgets can never drift again. No hex literals left loose in `spectracsMain.py`.
- All currently-hardcoded hex (`#33663d`, `#5A5A5A`, `#404040`, etc.) is replaced by getter reads.

---

## 5. Rubber-duck pass — does this actually deliver "consistent throughout"?

Talking it through skeptically, because tokens + getters are necessary but **not sufficient** for
the perceived consistency the user is after:

- **"A spacing scale doesn't enforce itself."** True. Five tokens still let every screen pick
  different ones. The consistency comes from the **application rules (§3.2)**, not the scale. The
  rules are the real contract; the tokens are just the vocabulary. → The spec must be audited
  *rule-by-rule per screen*, not just "are raw numbers gone?"
- **"Centralizing colors changes nothing visible."** Correct — §4.3 is a *refactor*, zero pixels
  move. Its payoff is preventing future drift and unlocking the palette, not fixing today's look.
  Don't oversell it as a visual fix. The thing the user actually *sees* improve is §3 (spacing) +
  reconciling the two greens (D1).
- **"Borders were called out but we're barely touching them."** Right, and that's the correct
  call — they're already consistent. But the *abandoned commented-out borders* in the calibration
  view (`border:1px solid #00000000`) signal a structure that was wanted and removed. The spec
  should decide deliberately: either cards get a real border (per §3.2) or they don't — don't leave
  the ambiguity that caused the comment in the first place.
- **"Charts are the real visual outliers."** The negative-margin hacks mean charts sit differently
  from every other panel. Fixing those (§3.2) is probably the single most *visible* harmony win,
  more than any color change. Prioritize it.
- **"Custom-painted widgets bypass QSS entirely."** Hough lines, scatter series, toggle switch use
  QColor directly. Consolidating onto the singleton getters is what keeps *those* in sync with the
  QSS theme — this is the one place where the color refactor (§4.3) genuinely prevents a visible
  mismatch, so it's worth doing.
- **Risk / non-goal:** this is **not** a redesign. No new layouts, no restructured screens, no new
  components. If mid-implementation we find a screen that's inconsistent because its *structure* is
  wrong (not its spacing/color), that's logged for a separate discussion — not fixed here.

**Verdict:** the plan is sound but its consistency payoff is **front-loaded in §3 (spacing rules)
and D1 (one green)**; §4 is insurance, not a visible win. Sequence the work so the visible wins land
first and are reviewable on their own.

---

## 6. Implementation phases (tabular)

> Phases are ordered so each is independently reviewable and the **visible** improvements come first.
> Nothing here is executed until explicitly requested.

| Phase | Title | What it does | Touches | Visible change? | Depends on |
|-------|-------|--------------|---------|-----------------|------------|
| P0 | Tokens + getters (scaffolding) | Add `Metrics` (5 spacing tokens) and the new color getters (semantic roles + neutral ramp) to `style/`. No call sites switched yet. | `style/ApplicationStyleLogicModule.py`, new `style/Metrics.py` | No | — |
| P1 | One green | Reconcile `#3D7848` vs `#33663d` per D1 across QSS, logo SVG, chart pens. | `spectracsMain.py`, `MainStatusBarViewModule.py`, `SpectralJobGraphViewModule.py` | **Yes (subtle)** | P0 |
| P2 | Chart margins | Remove negative layout margins; set chart's own margins to 0. | the 2 chart/interpolation view modules | **Yes (clear)** | P0 |
| P3 | Spacing rules | Apply §3.2 contract: page margins `M`, sibling `setSpacing(S)`, card padding `S`. Replace all ad-hoc `setContentsMargins`. | `PageWidget.py` + ~11 margin call sites + main layouts | **Yes (biggest)** | P0, P2 |
| P4 | Border decision | Decide cards-have-border vs not; resolve the commented-out calibration borders deliberately. | calibration view modules, QSS card rule | **Yes (subtle)** | P3 |
| P5 | QSS from getters | Rewrite the 380-line QSS to be generated from the getters; remove all loose hex literals. Pure refactor. | `spectracsMain.py` | No | P0, P1 |
| P6 | Painted widgets onto getters | Route Hough lines / scatter / toggle switch / inline `setStyleSheet` sites through the getters. | calibration video/interpolation modules, `ToggleSwitch.py`, 3 inline `setStyleSheet` sites | No (prevents drift) | P0, P1 |
| P7 | Semantic palette adoption | Apply `info`/`warning`/`danger` where status is shown (e.g. "expected detection", calibration pass/fail, out-of-range). | status-bearing widgets (TBD list) | **Yes (new)** | P0, P5, P6 |
| P8 | Consistency audit | Walk every screen against §3.2 rules + role usage; log structural (not spacing/color) inconsistencies as separate follow-ups. | review only | — | all above |

### Suggested grouping for review
- **Visible-wins batch:** P1 → P2 → P3 (+ P4). Reviewable on screenshots; the harmony the user asked for.
- **Insurance batch:** P5 → P6. Pure refactor, no pixels move; review by diff + "still looks identical".
- **Expansion batch:** P7 → P8. The new semantic colors + final sweep.

### Phase status
- **P0–P6: SPECIFIED, awaiting go.** This is the agreed scope to implement first. Not yet implemented.
- **P7–P8: DEFERRED.** Direction captured in §7.1; concrete decisions (7b thresholds, 7c application,
  status-widget list) happen when P5/P6 are done. Do **not** start P7 with the P1–P6 go.

---

## 7. Decided defaults (was: open items)

All previously-open items now have an agreed default; none blocks P1–P6.

| Item | Decision | Revisit at |
|------|----------|-----------|
| `warning` / `danger` hex | Default `#C9942E` / `#B0544E`; eyeball on a real screenshot, nudge then | P7 |
| Cards: border vs none | **No extra border** — rely on `surface` gray contrast (cleaner, less boxy); revisit only if flat | P4 |
| Status-widget list for semantic colors | **Deferred** — discover by screen walk, propose list then | P7 |
| Over-greening guard (7d) | **Green stays everywhere for now**; demotion list captured in detail later | P7 |
| Disabled vs semantic (7e) | Reuse existing disabled treatment; semantic only when enabled | P7 |

### 7.1 Phase 7 anticipated decisions (deferred — not part of the P1–P6 go)

| # | Decision | Agreed direction |
|---|----------|------------------|
| 7a | State → role mapping | calibration **failed = `danger`** ✓; low-confidence / out-of-range = `warning`; hints = `info`; pass = `success` (green) |
| 7b | Numeric thresholds (warning vs danger) | **RANSAC is no longer used** — threshold source TBD (peak-confidence / consensus matcher). Domain call, needs Edwin. Deferred with P7. |
| 7c | How the color is applied (bg / text / border / badge) | **Postponed** — decide alongside the status-widget walk |
| 7d | Over-greening guard | **Postponed** — green everywhere for now, demotion list later |
| 7e | Disabled vs semantic | Reuse existing disabled treatment |

---

## 8. Final rubber-duck — go/no-go for P1–P6

Second skeptical pass, this time only on the batch about to be greenlit. The first pass (§5) asked
"is the plan sound?"; this one asks "is P1–P6 actually safe and complete enough to start?"

- **P1 — is there really only one extra green?** The scan found `#3D7848` and `#33663d`. Reconciling
  must also catch the **embedded logo SVG** (`#33663d` strokes in `MainStatusBarViewModule.py`) and
  the **chart pen** in `SpectralJobGraphViewModule.py` — both easy to miss because they're not in the
  QSS. P1's "touches" list names them; the risk is a *third* shade hiding in a custom-paint call.
  → Mitigation: before P1, grep every `#33663d`/`3D7848`/`fromRgb(61,120,72)`/`fromRgb(51,102,61)`
  occurrence and confirm the list is exhaustive. **Cheap, do it first.**
- **P2 — will zeroing chart margins actually look right?** Removing `(-20,-10,-10,-10)` and setting
  the chart's own margins to 0 assumes the negatives were *pure* compensation. If any negative was
  also hiding a clipped axis label, zeroing reveals it. → Mitigation: P2 is screenshot-reviewed
  per chart; treat axis-label clipping as the acceptance check, not just "margins gone."
- **P3 — the ordering trap.** P3 depends on P2, good. But P3 also rewrites `PageWidget`'s margins
  (`(0,5,5,5)` today), which is the *container every page sits in*. A change there moves **every**
  screen at once — high blast radius, high payoff. → Mitigation: do `PageWidget` as its own
  reviewable commit *within* P3, separate from the leaf call sites, so a regression is bisectable.
- **P4 — we defaulted to "no border," but the comment existed for a reason.** Someone wanted
  structure there. "No border" may re-create the exact flatness that prompted the experiment. →
  Mitigation: P4 acceptance = look at the calibration screen specifically; if panels blur together,
  the default flips to a `1px` border. Cheap to reverse.
- **P5/P6 — "pure refactor" is the dangerous words.** Generating the QSS from getters and routing
  painters through getters must produce **byte-for-byte the same colors**. Any getter whose hex
  doesn't exactly match the literal it replaces is a silent visual change masquerading as a no-op. →
  Mitigation: P5/P6 acceptance = a before/after screenshot diff that shows **zero** pixel change. If
  anything moves, a getter value is wrong, not the approach.
- **Cross-cutting — no automated safety net.** There are no visual-regression tests; every phase is
  eyeballed. That's acceptable for this app's size but means **discipline = one phase per commit,
  screenshot each.** Skipping that is the only real way P1–P6 goes wrong.
- **Scope honesty:** P1–P6 will *not* make the app look redesigned. It removes the "dirty"
  inconsistency (mismatched greens, random gaps, outlier charts) and lays the color plumbing. The
  *new* look (semantic status colors, deliberate green-demotion) is P7 — deferred. Expect "cleaner
  and calmer," not "different."

**Verdict: P1–P6 is GO-ready**, conditional on three cheap disciplines: (1) exhaustive green grep
before P1, (2) one-phase-per-commit + screenshot each, (3) P5/P6 judged by zero-diff screenshots.
No blocking unknowns remain in this batch.
