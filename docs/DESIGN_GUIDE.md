# Spectracs UI — Design Guide

Conventions for building views, so later screens stay consistent. Distilled from the existing
`PageWidget` framework, the global stylesheet (`ApplicationStyleLogicModule`), and lessons from the
User-admin screens (Roadmap #4). Pairs with `SPEC_visual_harmonization.md` (the colour/border spec)
and `Metrics` (spacing constants).

---

## 1. Page layout: two patterns — pick deliberately

Every page is a `PageWidget`; its `getMainContainerWidgets()` returns an ordered dict of rows stacked
vertically. **How the vertical space is used depends on the page's job:**

### A. Hub / menu page — *spread* over the full height
Few, large controls (big buttons / group boxes) that should fill the panel so the screen reads as a
deliberate menu. **This is the default** (`compactMainContainer = False`).
Example: `SettingsViewModule` — group boxes with `setRowStretch(i, 15)`, buttons span the height.

### B. Form / editor page — *compact*, packed at the top
A handful of labelled fields. Spreading them over the height looks broken (huge gaps between 4–5
rows). Set **`compactMainContainer = True`** on the `PageWidget` subclass — a trailing stretch row
absorbs the slack so fields sit at natural height at the top.
Example: `UserViewModule`.

> Rule of thumb: **list/menu of actions → spread (A); a form you fill in → compact (B).**
> If a new editor looks like fields floating in space, you forgot `compactMainContainer = True`.

## 2. Labelled fields

Use `PageWidget.createLabeledComponent(label, widget)` — lays the `PageLabel` at 30 % and the field
at 70 %. Stack each via the `getMainContainerWidgets()` dict. Don't hand-roll grids per field.

## 3. Booleans / checkboxes

`QCheckBox` (and `QRadioButton`) **is a `QAbstractButton`**, and the theme styles every button with a
solid-green 50 px fill. The global stylesheet now resets checkbox/radio *backgrounds* to transparent
(incl. `:hover`/`:pressed`) so only the indicator shows — but two things are on **you**:

- **Height:** the 50 px button height still applies. For a tidy form row, set a compact height in code:
  `checkBox.setFixedHeight(22)`. (Not done globally because the custom `ToggleSwitch` needs its own size.)
- **Don't let it stretch across the 70 % column:** wrap it so it sits left at natural width —
  `QHBoxLayout` with the checkbox + `addStretch(1)` — then pass that wrapper to
  `createLabeledComponent`. Otherwise the indicator floats in a wide empty cell.

For an on/off control that should look like a switch, reuse `ToggleSwitch` instead of a bare checkbox.

## 3b. Button variants (semantic roles)

Buttons are **primary** green by default (Bootstrap nomenclature). For a semantic role, tag the button
in view code: `button.setProperty("buttonType", "secondary" | "info" | "danger")` (set it **before**
the widget is shown). The QSS recolours it from the palette:
- `secondary` — neutral gray `#404040` (same as the PageLabel background) for non-primary actions.
- `info` — light gray `#8A8A8A` **placeholder for now** (overrides spec D3's teal until a real info
  hue is chosen).
- `danger` — muted red `#B0544E`.

Example: the login dialog's **Cancel** is `secondary` (gray) so it reads as the non-primary action.
Add new variants by extending the palette getters + the `QAbstractButton[buttonType="…"]` rules.

## 4. Tables / lists

- A selectable grid → `QTableView` + a `QAbstractTableModel`; `SelectRows`, `SingleSelection`,
  `NoEditTriggers`. **Hide the vertical header** (`verticalHeader().setVisible(False)`) — otherwise an
  empty row-number gutter shows on the left. `horizontalHeader().setStretchLastSection(True)`.
- A rich rows-as-cards list → `QListView` + `QAbstractListModel` + an HTML delegate
  (see `SpectrometerProfileListViewModule`).
- Standard nav buttons live in `createNavigationGroupBox()`: **Back** first, then actions
  (Add / Edit / Delete / Save). Double-click a row = Edit. Destructive actions confirm via `QMessageBox`.

## 5. Data freshness (server-backed screens)

A `PageWidget` builds its widgets **once** (at app startup, via `MainViewModule`). If the page shows
data that depends on login or a server (anything behind `SpectracsPyServerClient`), **re-fetch in
`showEvent`** — navigation makes the page visible and fires `showEvent`, so every visit reloads with
the current session. Relying on the build-time load alone freezes the page on its startup (logged-out)
state. (This was the Roadmap-#4 "Not authorized / empty table" bug.)

For local, login-independent data, the build-time load + a CRUD signal refresh is enough
(`SpectrometerProfileListViewModule`).

## 6. Registering a new page (three hardcoded touch-points)

1. `MainViewModule.__init__` — instantiate, `.initialize()`, `addWidget` (note the index).
2. `NavigationHandlerLogicModule` — add the target string to **both** `if/elif` chains
   (`handleNavigationSignal` title + `__getWidgetIndex`) with that index.
3. The launching view — emit a `NavigationSignal` with `setTarget("<YourViewModule>")`.

## 7. Role gating

Master-only entry points: gate visibility on
`CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value)`, and reconnect on `userSessionSignal`
so it updates on login/logout (see `SettingsViewModule.updateAdministrationVisibility`). Add a
defense-in-depth check in the gated page itself (don't rely on the hidden button alone).

## 8. Stylesheet gotchas (`ApplicationStyleLogicModule`)

- It's **one big QSS template**; an invalid token makes Qt reject the **whole** sheet
  (`Could not parse application stylesheet`) and the app renders unstyled. Validate after edits by
  launching with a polished widget — the warning only fires on polish, not at `setStyleSheet`.
- Unsupported in Qt QSS: `height: auto`, `background-color: none`. Use real values
  (`transparent`, a length, omit).
- **Selector order matters:** equal-specificity rules → the *later* one wins. To override a base rule
  (e.g. `QAbstractButton`), place your override **after** it.
- When editing, watch the `{{` / `}}` escaping (the template is `str.format`ed) and never drop an
  adjacent selector line — a missing `Selector {` orphans the next block and breaks parsing.
- **Partially-styled buttons fall back to native frames:** if you set a button's `background` but no
  `border`, a default/focused button (e.g. a dialog's default button) renders the native blue
  default-frame. `QAbstractButton` sets `border: none` to suppress it — keep that when restyling buttons.
