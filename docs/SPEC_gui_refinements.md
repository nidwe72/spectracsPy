# Spec — GUI refinements (maximized start · dead-button cleanup · no native windows)

Status: **DONE — IMPLEMENTED + verified 2026-07-06 (G1–G6).** GUI brushup, all app-repo: maximized start;
in-window dialogs rendered as opaque stacked-view pages (footer buttons, vertically centred); desktop login
inlined + laid out (centred, capped width, Register in body full-width, clear+focus on open); dead-button /
connect-screen teardown + renumber; Settings reorg (Administration order, new Development section, About/Help
inline dialogs); `Ctrl+L` account shortcut. Verified by headless boots + offscreen renders; Edwin
click-through-approved ("happy with the GUI brushup"). As-built per section + §As-built.

---

## G1 — Desktop starts maximized

`spectracsMain.py` (:130-134, the desktop `else` branch) sets a minimum size then `show()`. Change to
**`showMaximized()`** so the app opens maximized on the desktop. Leave the other two branches untouched:
Android `showFullScreen()` (:117) and desktop **phone-mode** fixed-width `show()` (:127-129, the audit
invariant — must NOT be maximized).

```
else:
    geometry = QGuiApplication.primaryScreen().availableGeometry()
    mainContainerViewModule.setMinimumWidth(geometry.width() / 2)
    mainContainerViewModule.setMinimumHeight(geometry.height() * 0.9)
    mainContainerViewModule.showMaximized()   # was show()
```

Trivial; no open questions.

---

## G2 — Remove unused Settings buttons

Latest Settings screenshot (2026-07-05_23-19) flags (1)–(5) as no longer needed. Verified against
`SettingsViewModule.py`:

| # | Button | Handler? | Verdict (Edwin 2026-07-06) |
|---|---|---|---|
| 1 | **Connect spectrometer** | yes → `SpectrometerConnectionViewModule` (+ legacy register-by-serial) | **REMOVE** + retire the connect screen |
| 2 | Device calibration (legacy) | — | already removed (§11) |
| 3 | **Measurement profiles** | none (dead) | **REMOVE** (button + section) |
| 4 | **Evaluation profiles** | none (dead) | **REMOVE** (button + section) |
| 5 | **Upload profiles** | none (dead) | **REMOVE** (button + section) |
| — | **Repository profiles** (Downloads) | none (dead) | **KEEP** — future home for server-connection / repo config (see note) |
| — | Measurement profile **combo** (Acquisition) | empty | remove (dead; confirm) |
| — | About / Help (Infos) | none | **KEEP** (placeholders) |

- **RESOLVED:** remove **(3)/(4)/(5)** and their now-empty group boxes (`Evaluation profiles`, `Uploads`).
  **Keep the `Downloads` / Repository profiles section** — Edwin: it will become where things like the
  **`spectracsPy-server` connection details** are specified. *(Note also parked in
  `SPEC_connection_and_calibration_ux.md` cross-refs / this file's §Notes.)*
- **RESOLVED — (1) Connect spectrometer: REMOVE.** Connection is now surfaced by the **header camera
  indicator + targeted autoconnect** (§4.4/C3) and end users bind their serial at **registration**, so the
  manual connect screen is obsolete. Removing the button orphans `SpectrometerConnectionViewModule` +
  `RegisterSpectrometerProfileViewModule` → **retire both** (delete files, unwire `MainViewModule` + the two
  `NavigationHandler` ladders, **renumber** the nav stack; app currently starts on the connection screen —
  change the startup default to `Home`/`Login`).
- **RESOLVED — About/Help: KEEP** as placeholders.

**Server-connection config note (parked):** the **Downloads** section is the intended home for
`spectracsPy-server` connection details (host/port, currently hard-coded in
`SpectracsPyServer.NAMESERVER_PORT`/`DAEMON_NAT_HOST`) and repository config. Not designed yet — a later task.

After cleanup the Settings screen = **Acquisition** (Virtual Spectrometer) · **Downloads** (Repository
profiles, placeholder) · **Infos** (About / Help) · **Administration** (Users / Playground / Plugins /
Spectrometer setups).

---

## G3 — No separate OS windows (everything in-window)

`InWindowDialog` (`view/application/widgets/InWindowDialog.py`) already renders dialogs **inside** the
top-level window — a dimmed scrim + centered themed card, run on a nested event loop — and is used **44×** for
notify/confirm. It never creates a second OS window (that also fixes the Qt-for-Android EGL-surface crash).
So the pattern exists; the job is to route the **last few native-window sites** through it. Audit of live code:

| Site | Kind | Fix |
|---|---|---|
| `MainStatusBarViewModule.py:244` — `ServiceLoginDialog(self); dialog.exec()` (desktop account login) | `QDialog` (top-level window) | **RESOLVED:** use the in-window `LoginViewModule` on desktop too (already the Android twin, navigated to at :240). Make both branches navigate to `LoginViewModule`; **delete `ServiceLoginDialog`**. → *login LOOK sub-question below.* |
| `SpectrometerCalibrationProfileWavelengthCalibrationViewModule.py:105` — `QDialog` showing `expectedDetection.png` ("help: expected detection") | `QDialog` | **RESOLVED — inline:** add an image variant to `InWindowDialog` (e.g. `InWindowDialog.showImage(host, title, pixmap)`), reused for future image help. |
| `VirtualSpectrometerViewModule.py:96` — `QFileDialog.getExistingDirectory` (virtual capture folder) | native **folder** picker | **RESOLVED — keep native** (desktop-only exception) |
| `SpectralJobImportViewModule.py:58` — `QFileDialog` AnyFile (import a spectrum file) | native **file** picker | **RESOLVED — keep native** (desktop-only exception) |

- **QMessageBox:** the 4 `QMessageBox` occurrences are all in **comments/docstrings** — no live QMessageBox
  windows remain (the migration to `InWindowDialog.notify/confirm` is already complete).
- **RESOLVED — `QFileDialog` stays native on the desktop** (Edwin). It's the one documented exception to
  "no native windows" — a native file/folder browser is desktop-only and an in-window browser is a sizable
  build not worth it now. (Android uses a different capture-image mechanism; revisit if/when Android needs it.)
- **Login look — RESOLVED: full-page, prominent (Q4, Edwin).** `LoginViewModule` is already a full **page** on
  the stack (the phone was never a `QDialog`; the "dialog" memory is the **desktop** `ServiceLoginDialog`).
  Desktop switches to the same full-page login, rendered **prominent**. Per §G4 the **Register** button moves
  from the footer into the **main window body**; the footer keeps the primary **Login** (+ Back).

---

## G4 — Action buttons live at the bottom (footer convention)

Edwin: **confirm/cancel buttons belong in the app footer**, not floating in a centered card; and on the login,
**Register belongs in the main window body**, not the footer. Underlying principle: *the primary decision
buttons sit at the bottom (thumb-reach / consistent placement); mode-switch links sit in the body.*

**Grounding — there is NO global footer widget.** `MainContainerViewModule` = header (`MainStatusBarViewModule`)
+ the page stack (`MainViewModule`); each **page** renders its own bottom nav bar. So "footer" = *the bottom
button bar of the current surface*, not a shared widget.

**G4a — `InWindowDialog` renders as a STACKED-VIEW page (not an overlay).** Edwin: the scrim + floating card
"looked like an overlay"; it should look like a **stacked view** (a page that replaces the current one).
`InWindowDialog` now paints an **opaque** page background (`getBackgroundColor()`, no scrim) and lays out like
any page: the title/message/image block is **vertically centered** (top+bottom spacers — little-content
dialogs read better centered; tall content fills as the spacers collapse), with action buttons in a
**full-width footer bar at the bottom** (Cancel = secondary/gray, Confirm = primary green, destructive = red). Mechanically it is still an
overlay widget on the top-level window running a **nested event loop**, so `confirm()`/`notify()`/`showImage()`
stay **synchronous** and never spawn a second OS window — **no API change → all 44 call sites untouched**.
*(Deliberately kept as an overlay-widget-that-looks-like-a-page rather than a real `QStackedWidget` page:
`confirm()` must return `bool` synchronously; a real stack page would force an async rewrite of every caller.)*

**G4b — Login: Register in the body.** In `LoginViewModule`, move **Register** out of the nav footer into the
**form body** (a secondary link/button, e.g. under the password field: "New here? Register"). Footer keeps the
primary **Login** (+ Back). Aligns the login with the footer convention (primary action in the footer,
mode-switch in the body).

**Consistency note:** login = a full **page** (a destination), confirm = an **overlay** (a transient
synchronous decision). Different mechanisms, same rule — the decision buttons render at the bottom.

---

## G5 — Reasonable max content width (IMPLEMENTED 2026-07-06, login only)

**Decisions (Edwin):** value **560**; content caps while the **footer stays full-width**; scope **login only**
(NOT the dialogs, NOT Registration — the constant is defined for reuse, but only Login opts in for now).
As-built: `Metrics.CONTENT_MAX_WIDTH = 560`; new opt-in `PageWidget.maxContentWidth` caps the content column at
the constant + centres it with side spacers (nav footer stays full-width); phone/Android width < cap → no
effect. `LoginViewModule` opts in (`maxContentWidth = True`). Render-verified (login capped + centred, footer
full-width). `InWindowDialog` intentionally **not** capped (stays full-width) for now.

### Original design

Edwin: on a maximized desktop window the login form (and dialogs) stretch full-width, which reads poorly. A
short form should cap at a **reasonable max width**, defined **once as a constant** and reused where
appropriate.

- **Constant:** add `Metrics.CONTENT_MAX_WIDTH` (single source of truth, alongside the spacing scale).
  Proposed **≈ 560 px** — comfortable for the label(30%)+field(70%) rows; TBD/tunable.
- **Behaviour is desktop-only for free:** cap via `setMaximumWidth(CONTENT_MAX_WIDTH)` + horizontal centring.
  On phone-mode / Android the window is narrower than the cap, so it never binds → full width. No branching.
- **Apply to:**
  - **Login** (`LoginViewModule`): cap + centre the field block. Footer nav (Login/Back) stays **full-width**
    (page footer).
  - **`InWindowDialog`**: cap + centre the title/message **content column**. Footer buttons stay
    **full-width** (the app-footer convention from §G4). *(Images keep their own larger scaled width — the
    constant governs text/form columns, not image help.)*
  - Other short forms if wanted (Registration). Wide editors (plugin/setup) are unaffected.
- **Mechanism:** a reusable opt-in on `PageWidget` (e.g. `maxContentWidth` → wrap/centre the main container at
  the constant), plus a direct cap in `InWindowDialog`; both reference `Metrics.CONTENT_MAX_WIDTH`.
- **Open:** (a) the value (≈560?); (b) confirm footer stays full-width while content caps (recommended);
  (c) which extra screens opt in (Registration?).

## G6 — Settings reorg, login behaviour, account shortcut (IMPLEMENTED 2026-07-06)

Follow-on GUI tweaks (Edwin), all app-repo:
- **Settings › Administration** re-ordered to **Spectrometer setups · Users · Plugins**.
- **Playground** moved out of Administration into a new **Development** section (master-gated, same as
  Administration).
- **About** → inline dialog (`InWindowDialog.notify`) showing name + version (`APP_NAME` / `APP_VERSION`
  constants on `SettingsViewModule`; version `1.0.0` is a placeholder until a real source is wired).
- **Help** → inline dialog with a 2-sentence generic description of the app.
- **Login behaviour** (`LoginViewModule`): on `showEvent` the fields are **cleared** (so nothing lingers after
  logout) and the **username is focused** (deferred one tick). Username/Password share one grid (`createForm`)
  for a uniform label column; the **Register** button spans the **full (capped) form width**, edges aligned
  with the labels/fields.
- **`Ctrl+L` account shortcut** (app-wide, in `MainStatusBarViewModule`): same as the account icon — opens the
  login view when logged out, the account (Logout) menu when logged in.

## Decisions (Edwin 2026-07-06)
- **Q1 Connect spectrometer:** REMOVE + retire the connect screen.
- **Q2 About/Help:** KEEP.
- **Q3 QFileDialog:** KEEP native on the desktop (documented exception).
- **Q4 login look:** full-page, **prominent** (not a card).
- **Repository profiles (Downloads):** KEEP (future server-connection config).
- **G4:** confirm/cancel → footer bar in `InWindowDialog`; login **Register** → body.

## Implementation phases (all app-repo; no model/server)

```
 PH   WHAT                                                          KEY TOUCHPOINTS / NOTES
 ───────────────────────────────────────────────────────────────────────────────────────────────────────
 P1  G1 maximized desktop start                                    spectracsMain.py desktop `else`:
                                                                   show() → showMaximized()
 P2  G4a InWindowDialog confirm/notify buttons → bottom footer     InWindowDialog.py ONLY (layout change);
      bar (scrim+card message above; full-width footer buttons).   nested loop + confirm()/notify() API
      NO API change → 44 call sites untouched.                     unchanged → 44 callers untouched
 P3  G3a desktop login → in-window LoginViewModule (both branches  MainStatusBarViewModule (:244 branch);
      navigate there); DELETE ServiceLoginDialog. G4b: move        LoginViewModule (Register→body, footer
      Register into the login body; footer = Login (+Back).        Login/Back); delete ServiceLoginDialog.py
 P4  G3b expected-detection image → inline                         +InWindowDialog.showImage(host,title,
      InWindowDialog.showImage; wavelength view uses it.           pixmap); WavelengthCalibrationViewModule
 P5  G2 remove dead buttons (3/4/5) + their sections; KEEP         SettingsViewModule (buttons/sections);
      Downloads/About/Help. REMOVE Connect spectrometer +          delete SpectrometerConnectionViewModule +
      RETIRE connect screen (delete SpectrometerConnection +       RegisterSpectrometerProfileViewModule;
      RegisterSpectrometerProfile); unwire Main/Nav + RENUMBER;    MainViewModule + NavigationHandler (both
      startup default (currently the connect screen) → Home.       ladders) + spectracsMain default view
 P6  verify: headless boot + index consistency; no live QDialog/   boot test (widget↔index); grep no
      ServiceLoginDialog; render checks (footer buttons, login).   ServiceLoginDialog / connect refs
 ───────────────────────────────────────────────────────────────────────────────────────────────────────
 Independent: P1, P2, P4 stand alone. P3 deletes ServiceLoginDialog. P5 is the teardown+renumber (do last).
 Native windows remaining after: only the 2 documented desktop QFileDialog pickers (Q3).
```

Suggested order: **P1 → P2 → P3 → P4 → P5 → P6** (quick wins first; the teardown+renumber last).

## As-built (IMPLEMENTED 2026-07-06, app-repo only, uncommitted)
- **P1** `spectracsMain.py` desktop `else` → `showMaximized()`.
- **P2** `InWindowDialog` rewritten to look like a **stacked view** (Edwin: the scrim+card read as an
  overlay): **opaque page background** (no scrim), title at top, message/image in the body, **buttons in a
  full-width footer bar at the bottom** (nav-button style; destructive = red). Still an overlay widget +
  nested loop under the hood → `confirm()`/`notify()`/`showImage()` stay synchronous, API unchanged, all 44
  call sites untouched. Verified by render (confirm + image both read as pages).
- **P3** `MainStatusBarViewModule` — both login branches navigate to the in-window `LoginViewModule`;
  **`ServiceLoginDialog.py` deleted**. `LoginViewModule` — **Register moved to the body** ("New here?
  Register"); footer = Login / Back; content **vertically centred** via a new opt-in
  `PageWidget.verticalCenterMainContainer` flag (leading spacer to match the compact trailing one) so the
  short form sits mid-height instead of top-packed.
- **P4** `InWindowDialog.showImage(host, title, pixmap)` added; the wavelength view's "expected detection"
  help uses it (no `QDialog`).
- **P5** `SettingsViewModule` — removed the dead Measurement-profile combo + Measurement/Evaluation/Upload
  buttons & their sections; **kept** Downloads (Repository profiles = placeholder for future server-connection
  config), About/Help, Administration. **Removed Connect spectrometer** + **deleted**
  `SpectrometerConnectionViewModule` + `RegisterSpectrometerProfileViewModule`; unwired `MainViewModule` +
  both `NavigationHandler` ladders, **renumbered** (Connection idx-6 gone → everything below −1; setup
  list/editor → 13/14, registration → 15; **16 stack widgets**, was 17); **startup default → Home** (was the
  connect screen).
- Remaining native windows: only the two documented desktop `QFileDialog` pickers (Q3) + the desktop account
  `QMenu` popup (not in scope — logout menu; convert later if wanted).
