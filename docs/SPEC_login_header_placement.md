# SPEC — Login control in header + full-width status bar

> Status: **IMPLEMENTED 2026-06-29** (phases P1–P5, §7; cosmetic polish §11). Offscreen render
> verified on the real dark theme in both logged-out (grey person-outline) and logged-in (green
> filled) states; progress bar spans full width; Settings page strips clean. `HEADER_CONTENT_HEIGHT
> = 70` (also de-distorts the logo, RD3). **As-built design + DoD: see §11** (it supersedes earlier
> design-time wording in D5/§4 where they differ — notably: no inline username label, flat bordered
> button, grey/green state colours). Realises **Roadmap item #2** (`spectracs-docs/ROADMAP.md`).
> Scope: **layout only** — the login
> *logic* already exists (Step 2a, commit `4a27172`). This moves the existing login control into the
> app header and widens the status/progress bar to full window width.

## 1. Purpose & scope

Roadmap #2 asks for two header-layout changes:

1. **Move the Login control** to the **right of the "spectracs" logo** (the common app-header
   pattern), with the **logo aligned left**.
2. The **status / progress bar** (below the logo) should **span the full window width**.

In scope: the header module `MainStatusBarViewModule` and relocating the login button out of the
Settings page. **Out of scope:** the auth/login *logic*, the `ServiceLoginDialog`, server calls,
roles — all already built and reused unchanged. The Home-page "Settings" navigation button is
**untouched** (it is unrelated navigation, not the login control).

## 2. Current state (as found)

### 2.1 Header = `MainStatusBarViewModule` (logo over progress bar)
`sciens/spectracs/view/main/MainStatusBarViewModule.py` — `MainStatusBarViewModule(QWidget)`,
`setFixedHeight(100)`. A **single-column `QGridLayout`**, vertical stack:

- **Row 0:** logo — a `QLabel` whose pixmap is rendered from an inline SVG (`logo_png`).
  Added `AlignCenter`, `setMinimumWidth(int(480 * 1.5))` = 720 (lines 24–38).
- **Row 1:** `QProgressBar`, `setMinimumWidth(int(480 * 1.5))` = 720, added with
  `alignment=AlignCenter` (lines 40–44).

The header sits in row 0 of the top-level `MainContainerViewModule` grid
(`view/main/MainContainerViewModule.py:28-33`); the page stack (`MainViewModule`, a
`QStackedWidget`) is row 1.

**Why the bar is not full-width today:** in a `QGridLayout`, giving a cell explicit
`alignment=AlignCenter` makes the widget take only its size hint, not the column width. Combined
with `setMinimumWidth(720)` and no `setColumnStretch`, the bar renders ~720 px, centered, regardless
of window width. The logo has the identical constraint.

### 2.2 Login control lives in the Settings page (not the header)
`sciens/spectracs/view/settings/SettingsViewModule.py`:

- A single `QPushButton` `self.serviceLoginButton` inside a "Service Login" `QGroupBox`
  (`createServiceLoginGroupBox`, lines 82–94), placed at row 4 of the Settings page grid.
- `updateServiceLoginButton()` (96–100): toggles text — `"Login"` when logged out,
  `"Logout (<username>)"` when logged in.
- `onClickedServiceLoginButton()` (102–110): if logged in → `CurrentUserSession().logout()`;
  else → open modal `ServiceLoginDialog`, and on success `CurrentUserSession().login(result)`.
  Then re-runs `updateServiceLoginButton()`.

Reached via: Home → "Settings" button → Settings page → Service Login group box. **Nothing is
adjacent to the logo.**

### 2.3 Supporting pieces (reused unchanged)
- `view/settings/login/ServiceLoginDialog.py` — modal username/password form; calls
  `SpectracsPyServerClient().login(...)` then `CurrentUserSession().login(result)`.
- `logic/session/CurrentUserSession.py` — `Singleton`, in-memory `userId/username/roles`;
  `isLoggedIn()`, `hasRole()`, `login()`, `logout()`. **No change-notification today** —
  whoever changes state must imperatively refresh its own button.
- `controller/application/ApplicationSignalsProviderLogicModule.py` — `SingletonQObject` with
  Qt `Signal`s (`navigationSignal`, `spectrometerProfileSignal`, `applicationStatusSignal`) and
  matching `emit…` methods. This is the existing app-wide signal bus the header already listens to
  for progress updates.

## 3. Decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Move vs. duplicate the login control | **Move** it to the header; **remove** the "Service Login" group box from `SettingsViewModule`. **One** login control, in the header. *(confirmed)* |
| D2 | Header layout shape | Replace the single-column vertical grid with a **`QVBoxLayout`**: row A = a **`QHBoxLayout`** header row (logo left · stretch · account control right); row B = the progress bar (fills width). Box layouts fill the cross-axis automatically — no `AlignCenter`/min-width fighting. |
| D3 | Logo alignment | **Left** (`AlignLeft | AlignVCenter`). Keep the SVG→pixmap rendering as-is. |
| D4 | Login-state sync across views | Add a new **`userSessionSignal`** to `ApplicationSignalsProviderLogicModule`; the account control refreshes on this signal. Future consumers stay correct without imperative coupling. (See §5.) |
| D5 | Login control form | An **account / person icon button** (cross-app convention), not a text button. Inline SVG glyph (matching the logo's SVG approach). Logged-out = person *outline* + tooltip "Login"; logged-in = filled icon + a small **username** label beside it. *(confirmed: icon, best-practice header pattern. **As-built, §11: the username label was dropped** — tooltip + click-menu suffice; icon is a flat **bordered** chip, grey-outline/green-filled.)* |
| D6 | Login control size | **Same height as the displayed logo**, both **vertically centered** in the 100 px header row. An icon is compact, so the logo keeps its native width/proportions — no crowding even at minimum window width. *(confirmed)* — **caveat (RD2):** the literal header band is 100 px; a 100 px-tall icon is oversized vs. the wordmark. Match the icon to the logo's *visual* glyph height (introduce one shared `HEADER_CONTENT_HEIGHT` driving both) and tune in P5, not the raw 100 px. |
| D7 | Login control behaviour | Reuse the existing logic: logged-out click → `ServiceLoginDialog` → `CurrentUserSession().login(...)`; logged-in click → a small popup menu showing the username with a **"Logout"** action (cleaner than a silent toggle, and shows *who* is signed in). Same `ServiceLoginDialog` / `CurrentUserSession` / `SpectracsPyServerClient`, only the *home* and *chrome* change. |
| D8 | Progress-bar width | **Full window width** — drop `AlignCenter`, set horizontal size policy **Expanding**, remove the 720 `setMinimumWidth`. (See §6.) |

## 4. Target header layout

Logged-out:
```
MainStatusBarViewModule (fixed height 100)
┌──────────────────────────────────────────────────────────────────────┐
│  [ spectracs logo ]                                            ( 👤 )  │  ← QHBoxLayout
│   left-aligned          ← addStretch() →     person-outline, tooltip "Login"
├──────────────────────────────────────────────────────────────────────┤
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ready for action...  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │  ← QProgressBar, full width
└──────────────────────────────────────────────────────────────────────┘
```
Logged-in *(as-built, §11 — no username label; green filled icon in the same bordered chip)*:
```
│  [ spectracs logo ]                                          [ 🟢👤 ]  │  green filled icon, bordered
```
Click logged-in → popup menu:  `edwin (master)` · `──────` · `Logout`

The account icon's height = the displayed logo height; both `AlignVCenter` in the 100 px row.

Construction sketch (illustrative, not final code):

```python
outer = QVBoxLayout(); outer.setContentsMargins(0, 0, 0, 0)
self.setLayout(outer)

headerRow = QHBoxLayout()
headerRow.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
headerRow.addStretch(1)
headerRow.addWidget(self.usernameLabel, alignment=Qt.AlignmentFlag.AlignVCenter)   # empty when logged out
headerRow.addWidget(self.accountButton, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
outer.addLayout(headerRow)

self.progressBar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
outer.addWidget(self.progressBar)            # no alignment → fills width
```

The account button is a `QPushButton` (or `QToolButton`) with `setIcon(...)` from an inline person
SVG and a square fixed size equal to the logo's display height; `setFlat(True)` for the icon-in-
header look. `updateAccountControl()` swaps icon + tooltip + username label per
`CurrentUserSession()` state.

Notes:
- Logo keeps `setScaledContents(True)` and its native width/proportions (D6) — the compact icon
  removes the earlier crowding concern, so no min-width reduction is needed.
- The `addStretch` guarantees the icon hugs the right edge regardless of window width.

## 5. Login control relocation + session signal

### 5.1 Add `userSessionSignal` to the signal bus
In `ApplicationSignalsProviderLogicModule`:
```python
userSessionSignal = Signal()                 # parameterless: "session changed, re-read CurrentUserSession"
def emitUserSessionSignal(self):
    self.userSessionSignal.emit()
```
A parameterless signal is enough — consumers read `CurrentUserSession()` directly. (A small
`UserSessionSignal` model could carry `isLoggedIn`/`username` if a typed payload is preferred, to
match the other signals' style — minor, decide during impl.)

### 5.2 Header owns the account control
Relocate the login logic from `SettingsViewModule` into `MainStatusBarViewModule` as an
**account-icon control** (D5/D7): an `accountButton` + `usernameLabel`, plus
`updateAccountControl()` (icon/tooltip/label per state) and `onClickedAccountButton()`
(logged-out → `ServiceLoginDialog`; logged-in → popup menu with **Logout**). Imports the same
`ServiceLoginDialog`, `CurrentUserSession`, `SpectracsPyServerClient` Settings used. After a
successful login/logout it calls `…getApplicationSignalsProvider().emitUserSessionSignal()`. The
header connects `userSessionSignal → updateAccountControl` (and calls it once at construction).

### 5.3 Remove from Settings
Delete the "Service Login" group box and its three methods from `SettingsViewModule`. The page grid
is rows 0–6; Service Login is **row 4** (`setRowStretch(4, 15)`). A `QGridLayout` does **not**
auto-collapse a vacated row (RD1), so simply removing the widget leaves an empty stretched band.
Re-flow concretely:

| was | becomes |
|-----|---------|
| row 4 `serviceLoginGroupBox` + `setRowStretch(4,15)` | **deleted** |
| row 5 `infosGroupBox` + `setRowStretch(5,15)` | row 4 + `setRowStretch(4,15)` |
| row 6 `navigationGroupBox` (no stretch) | row 5 |

Also drop the now-unused login imports from `SettingsViewModule` (`ServiceLoginDialog`,
`CurrentUserSession`, `SpectracsPyServerClient`) (RD9). No logic is lost — it relocated to the header.

## 6. Full-width progress bar

Changes in `MainStatusBarViewModule`:
- **Remove** `alignment=AlignCenter` when adding the progress bar.
- **Remove** `setMinimumWidth(int(480 * 1.5))` (line 41).
- **Set** `progressBar.setSizePolicy(Expanding, Fixed)`.
- With the `QVBoxLayout` (D2) and zero content margins, the bar now fills the full window width
  (the top-level `MainContainerViewModule` column already stretches edge-to-edge).

`resetProgressBar()` / `handleApplicationStatusSignal()` are unchanged.

## 7. Implementation phases (when requested)

Ordered so each phase leaves the app runnable. P1 has no dependents-before-it; P3 depends on P1+P2;
P4 depends on P3 (don't strip Settings until the header control works).

| Phase | File(s) | Change | Done-when |
|-------|---------|--------|-----------|
| **P1 — Signal** | `controller/application/ApplicationSignalsProviderLogicModule.py` | Add `userSessionSignal = Signal()` + `emitUserSessionSignal()` (§5.1). | App still starts; signal importable, nothing emits yet. |
| **P2 — Header restructure** | `view/main/MainStatusBarViewModule.py` | Single-column grid → `QVBoxLayout` with a header `QHBoxLayout`; logo `AlignLeft|AlignVCenter`; progress bar full-width — drop `AlignCenter` + `setMinimumWidth(720)`, set `SizePolicy(Expanding, Fixed)` (§6). Introduce `HEADER_CONTENT_HEIGHT` (RD2). | Logo sits left, progress bar spans full window width; no login control yet. |
| **P3 — Account control** | `view/main/MainStatusBarViewModule.py` (+ reuse `view/settings/login/ServiceLoginDialog.py`, `logic/session/CurrentUserSession.py`, `…/SpectracsPyServerClient`) | Add `accountButton` (flat `QToolButton`, inline person SVG icon, square = `HEADER_CONTENT_HEIGHT`) + `usernameLabel`; `updateAccountControl()` (icon/tooltip/label per state); `onClickedAccountButton()` (logged-out → dialog; logged-in → `QMenu` under the button with username + **Logout**); emit `userSessionSignal` after login/logout; connect `userSessionSignal → updateAccountControl`; call once at construction. | Login/logout works from the header; icon + username reflect state live. |
| **P4 — Strip Settings** | `view/settings/SettingsViewModule.py` | Remove Service Login group box + its 3 methods; re-flow rows 5→4, 6→5 and `setRowStretch` (§5.3 table); drop dead login imports (RD9). | Settings page has no login control and no empty gap row; app starts clean. |
| **P5 — Manual verify** | — (run the app) | Exercise all states (see checklist below). | All checks pass. |

**P5 checklist:** logged-out → person-outline icon at header right, tooltip "Login"; click → dialog;
successful login → icon reflects signed-in + `usernameLabel` shows the username; click → `QMenu`
with **Logout** → reverts to logged-out; **progress bar spans full width** and still animates on a
real capture/processing run; **Settings** page shows no login control and **no empty stretched row**;
icon height looks balanced against the logo (not oversized — RD2); check at the app's **minimum
window width** (no clipping/overlap).

## 8. Risks / edge cases

- **State desync:** the whole reason for §5's signal — any view showing login state must refresh via
  `userSessionSignal`, never assume it is the only mutator.
- **Narrow window clipping:** left logo + right icon could collide on small widths; the compact icon
  (D6) and the `addStretch` between them mitigate this. Verify at the app's minimum size (P5).
- **Header height:** the button lives in the fixed 100 px header row; ensure vertical centering so it
  is not stretched to 100 px tall (use the `AlignVCenter` flag, or a fixed button height).
- **Existing tests:** none cover this UI (pure layout); P5 is manual.

## 9. Decisions resolved (was: open questions)

1. **Move vs. duplicate** → **Move.** One login control, in the header; removed from Settings (D1).
2. **Styling** → **Account/person icon** (best-practice header pattern), inline SVG, with a username
   label + Logout popup menu when signed in (D5, D7).
3. **Size** → **Same height as the logo**, vertically centered; logo keeps native proportions, no
   min-width reduction needed (D6).

Remaining minor impl-time choices (no blocker): exact person-glyph SVG; whether the logged-in icon
shows a filled glyph or initials avatar.

## 10. Rubber-duck review (final pass)

Adversarial read of the spec against the actual code. Each finding is either folded into the spec
above (✅) or accepted as a known impl-time tune (◻).

| # | Finding | Resolution |
|---|---------|-----------|
| RD1 | **`QGridLayout` doesn't collapse a removed row.** Deleting Settings row 4 leaves an empty *stretched* band (`setRowStretch(4,15)` still applies). | ✅ §5.3 now gives the concrete renumber (5→4, 6→5) + stretch move. |
| RD2 | **"Same height as logo" taken literally = ~100 px icon** (header is `setFixedHeight(100)`), far larger than a normal header icon. | ✅ D6 caveat + P2 `HEADER_CONTENT_HEIGHT` shared by logo & icon; P5 verifies it looks balanced, not raw 100 px. |
| RD3 | **Logo already distorts** — a 480×100 pixmap with `setScaledContents(True)` + `setMinimumWidth(720)` is stretched ~1.5× horizontally *today*. | ◻ Pre-existing, **not** introduced here; left-aligning doesn't worsen it. Flagged so impl doesn't misattribute it. Out of scope to fix. |
| RD4 | **Self-emit loop risk:** the header emits `userSessionSignal` *and* listens to it. | ✅ Safe — the slot only reads `CurrentUserSession()` and repaints; it never re-emits. The signal exists for *decoupled future* consumers (#3/#4 user screens), not just self-refresh. |
| RD5 | **`usernameLabel` when logged out** must contribute zero width and clear on logout, or it pushes the icon left. | ✅ Empty text → zero width; `updateAccountControl()` sets `""` on logout. `addStretch` sits left of the label+icon pair so both stay right-anchored. |
| RD6 | **`QToolButton` vs `QPushButton`** for a flat icon-only header control. | ✅ Spec now recommends a flat `QToolButton` (idiomatic Qt for icon-only `autoRaise` chrome). |
| RD7 | **Popup-menu placement** — a bare `QMenu.exec()` pops at the cursor, not under the icon. | ◻ Impl note: `menu.exec(self.accountButton.mapToGlobal(QPoint(0, self.accountButton.height())))` to drop it under the button. |
| RD8 | **Signal-style inconsistency** — the other three bus signals carry typed payload models; this one is parameterless. | ◻ Accepted; §5.1 already offers a typed `UserSessionSignal` alternative if stylistic parity is wanted. No functional impact. |
| RD9 | **Dead imports** left in `SettingsViewModule` after the move. | ✅ P4 + §5.3 call out removing `ServiceLoginDialog` / `CurrentUserSession` / `SpectracsPyServerClient`. |
| RD10 | **Logged-in icon may not visibly differ** from logged-out if only the glyph swaps subtly. | ◻ The `usernameLabel` is the primary signed-in cue; icon fill/tint is secondary. Decide glyph treatment in P3, verify legibility in P5. |

**Verdict:** the design is sound and grounded in the code — one cross-module move + one layout
restructure + one small signal, all reusing existing auth logic. No blockers; the open items (RD3,
RD7, RD8, RD10) are either pre-existing or cosmetic impl-time tunes. **Ready to implement on
request.**

## 11. As-built & Definition of Done

What actually shipped (this section supersedes earlier design-time wording where they differ).

### 11.1 As-built deltas from the design
- **No inline username label (RD5/RD10 retired).** The earlier plan put a `usernameLabel` beside the
  icon; in review it was judged redundant. The signed-in user is surfaced by the **hover tooltip**
  (`"Signed in as <user> — click for options"`) and the **click menu** header (`<user> (<roles>)`).
  The `usernameLabel` widget was removed entirely.
- **State shown by icon colour, not a label.** Logged-out = **grey** person *outline*
  (`#808080`, the QSS form-label/readonly grey); logged-in = **green** filled person
  (`#3D7848`, brand/active). Hover brightens a shade (`#AAAAAA` / `#4E9A5E`) via QIcon `Active`-mode
  pixmaps — **never pure white**.
- **Flat bordered button (overrides the theme green).** The theme styles every `QAbstractButton`
  with a solid green background (`ApplicationStyleLogicModule` ~line 340). The account `QToolButton`
  carries its own stylesheet: `background: transparent; border: 1px solid #5A5A5A; border-radius:
  6px;` with a subtle light hover (`rgba(255,255,255,0.10)`) — a squared, slightly-rounded account
  chip, no green box.
- **`HEADER_CONTENT_HEIGHT = 70`** drives both the logo `setFixedHeight` and the square account
  button; at the 720 px logo width this ≈ native aspect, so it also **de-distorts the logo** (RD3).
- Icon glyph: a small inline person SVG (`PERSON_OUTLINE_SVG` / `PERSON_FILLED_SVG`, `%(c)s` colour
  token); **filled glyph**, not an initials avatar (RD10 resolved).

### 11.2 Definition of Done — per phase

| Phase | DoD | ✓ |
|-------|-----|---|
| **P1 Signal** | `userSessionSignal` + `emitUserSessionSignal()` on the bus; app starts. | ✅ |
| **P2 Header** | `QVBoxLayout` + header `QHBoxLayout`; logo `AlignLeft`; progress bar `Expanding`, **full window width**; `HEADER_CONTENT_HEIGHT` shared by logo+icon. | ✅ |
| **P3 Account control** | Flat bordered `QToolButton` at header right; grey-outline (logged-out) / green-filled (logged-in) icon + hover; click → `ServiceLoginDialog` or Logout `QMenu`; emits `userSessionSignal`; connected to `userSessionSignal → updateAccountControl`; init at construction. | ✅ |
| **P4 Strip Settings** | Service Login group box + 3 methods removed; rows re-flowed 5→4 / 6→5; dead imports dropped; **no empty stretched row**. | ✅ |
| **P5 Verify** | `py_compile` clean (3 files); offscreen smoke test (signal-driven refresh, both icons render, Settings has no `serviceLoginButton`); themed render of both states reviewed. | ✅ |

### 11.3 Acceptance criteria (overall)
- ✅ Login control is a single account-icon control at the **header right**, logo **left-aligned**.
- ✅ Status/progress bar **spans full window width** and still animates on status signals.
- ✅ Login/logout works from the header; state reflected live via `userSessionSignal`.
- ✅ Login control **removed from Settings**; Settings page lays out with no gap.
- ✅ No theme-green box; flat **bordered** chip; **grey/green** state colours (no pure white).
- ✅ No redundant inline username label (tooltip + menu suffice).
