# SPEC — GUI cosmetic tweaks (Settings entry moves to account menu · virtual-spectrometer save-images row · master-only fileset)

> Status: **P1–P3 IMPLEMENTED (desktop) + CLICK-THROUGH VERIFIED 2026-07-06.** **A** Settings moved from
> the Home footer into the logged-in account menu (§1); **B** the "save physically captured images" row
> removed (§2); **C** the virtual-spectrometer fileset is now **master-only** (§3). Offscreen-verified and
> confirmed by Edwin in the running app. Android account-menu handling remains **deferred** (§1.5).
> As-built in **§6**.

## 1. Item A — remove the Home-footer "Settings" button

### 1.1 As-found
`sciens/spectracs/view/home/HomeViewModule.py` — `createNavigationGroupBox()` builds a 4-button footer:
`New measurement` (col 0) · `Edit` (col 1) · `Delete` (col 2) · **`Settings`** (col 3, lines 69–72).
The `Settings` button calls `onClickedSettingsButton()` (lines 31–35) → navigates to `SettingsViewModule`.

### 1.2 The catch — Settings would become unreachable
`SettingsViewModule` is reached from **exactly one** forward entry: this Home-footer button
(`HomeViewModule.py:34`). Every other `setTarget("SettingsViewModule")` in the app is a **Back**
navigation *from a child of Settings* returning to it:
- `PlaygroundViewModule.py:217`, `PluginListViewModule.py:203/221`,
  `VirtualSpectrometerViewModule.py:194`, `SpectrometerSetupListViewModule.py:152`,
  `UserListViewModule.py:204/227`.

So removing the Home button leaves **no way to open Settings** from the top level. Settings still hosts
live, needed functions — the master **Administration** section (Spectrometer setups / Users / Plugins),
**Virtual spectrometer**, **Downloads**, **Infos**, **Development**. It cannot simply be orphaned.

### 1.3 Decision — A2: Settings entry in the account menu *(Edwin, 2026-07-06)*
Add a **"Settings"** `QAction` to the logged-in header **account menu** in
`MainStatusBarViewModule.onClickedAccountButton()` — the same menu that holds the disabled
`username (roles)` header, **Account settings…**, and **Logout**. On click → emit a `NavigationSignal`
to `SettingsViewModule` (same pattern as the "Account settings…" action already there).

**Accepted consequences of A2 (deliberate, not oversights):**
- **Login-gated.** Settings (About / Help / Downloads / master sections) is only reachable when logged
  in. Fine — the app effectively requires login for real use. Logged-out users have no Settings.
- **Desktop uses the native `QMenu`** (with the new "Settings" entry) — **no in-window workaround on
  desktop** (Edwin, 2026-07-06). The desktop experience stays a normal popup menu.

### 1.4 Proposed change
- Remove the `settingsButton` (`HomeViewModule.py:69–72`) and `onClickedSettingsButton` (31–35). The
  footer keeps `New measurement` / `Edit` / `Delete` in cols 0–2; col 3 simply isn't added (a
  `QGridLayout` with nothing in col 3 adds no stretch, so no empty band — verify in P4).
- In `MainStatusBarViewModule.onClickedAccountButton()` (desktop, logged-in branch): add
  `settingsAction = menu.addAction("Settings")` (above **Account settings…** or above **Logout**), and
  an `elif chosen == settingsAction:` that navigates to `SettingsViewModule` (mirror the existing
  `accountSettingsAction` block). Do **both** edits in one change so Settings is never orphaned (RD1).

### 1.5 Android note (DEFERRED — for the next Android impl/test)
The account menu is currently **skipped on Android**: `onClickedAccountButton()` has an `is_android()`
branch that logs out directly instead of calling `menu.exec()`, citing a Qt-for-Android single-window
popup crash (P4c). Consequence today: on Android a logged-in user can reach **neither** "Account
settings" **nor** (with A2) "Settings" — only Logout.

**⚠ Re-verify the premise first.** The "`QMenu.exec()` crashes on Android" claim is an **unverified
bring-up assumption** in the code, not a confirmed fact — and it is suspect, since `QComboBox` popups
(also popups) work on Qt-for-Android. So the **first Android task** is to *test whether the native
`QMenu` actually crashes*:
- **If it does NOT crash** → drop the `is_android()` special-case; Android uses the same native menu as
  desktop. Done, no workaround needed.
- **If it DOES crash** → give **Android only** an in-window account page (a stacked view like
  `LoginViewModule` / `InWindowDialog`: buttons Account settings · Settings · Logout). **Desktop keeps
  the native `QMenu`** regardless (§1.4). This fixes Account settings + Settings + Logout on Android in
  one move.

Not part of this cosmetic pass — deferred to the Android milestone (M4). Recorded here so it isn't lost.

## 2. Item B — remove the "save physically captured images" row

### 2.1 As-found
`sciens/spectracs/view/settings/spectral/spectrometer/acquisition/device/virtualCamera/VirtualSpectrometerViewModule.py`
(the "Virtual spectrometer" settings screen):
- Line 34: `result['doSavePhysicallyCapturedImagesComponent'] = self.createLabeledComponent('save
  physically captured images', self.__getDoSavePhysicallyCapturedImagesComponent())` — the row.
- Lines 18 & 21: `__doSavePhysicallyCapturedImagesComponent` field (declared twice — a dup).
- Lines 41–46: `__getDoSavePhysicallyCapturedImagesComponent()` (builds the `ToggleSwitch`).
- Lines 72–78: `onStateChangedDoSavePhysicallyCapturedImagesComponent()` (writes the setting).

### 2.2 Behaviour after removal (safe)
The setting `VirtualSpectrometerSettings.__doSavePhysicallyCapturedImages` **defaults to `False`** (model
`.../setting/virtualSpectrometer/VirtualSpectrometerSettings.py:17`) and is in-memory only. `VideoThread.
__captureFrame()` reads it purely to decide whether to also dump physical frames to `{appdata}/tmpImages`
(a dev/debug aid). Removing the toggle pins it at `False` — i.e. **the current default**; capture is
unaffected. No functional loss beyond the debug frame-dump, which was off by default anyway.

### 2.3 Proposed change
- **Minimal (recommended for a cosmetic tweak):** delete the row (line 34) + the component field, getter,
  and state-change handler. Leave the model field/getter/setter and the `VideoThread` branch as-is
  (harmless; setter simply becomes unused).
- **Optional thorough cleanup (own follow-up):** also drop the now-unused
  `get/setDoSavePhysicallyCapturedImages`, the field, and the `VideoThread` save branch. Larger blast
  radius (model + video path) — keep out of this cosmetic pass unless Edwin wants the dead code gone.
- While here: collapse the **duplicate** `__doSavePhysicallyCapturedImagesComponent` field declaration
  (lines 18 & 21) — it is removed entirely anyway.

## 3. Item C — virtual-spectrometer fileset is master-only

### 3.1 Intent (Edwin)
Only a **master** should set the virtual-spectrometer fileset. Workflow: log in as **masterUser** →
open Virtual Spectrometer → "Set image folder…" (loads the calibration/reference/sample set) → **logout**
→ log in as an **end user** → **measure** (measurement consumes the master-set fileset). The end user
never sets the fileset.

### 3.2 As-found
`SettingsViewModule` (§ read) currently exposes **"Virtual Spectrometer"** under the **Acquisition**
section (`createAcquisitionSettingsGroupBox`, lines 61–81) → navigates to `VirtualSpectrometerViewModule`.
Acquisition is **not** role-gated (visible to everyone). The master-only sections **Administration** and
**Development** are gated by `updateAdministrationVisibility()` (lines 135–138, driven by
`userSessionSignal`). So today an end user *can* reach the Virtual Spectrometer screen and set the fileset.

### 3.3 Proposed change (recommended)
- **Gate the Virtual Spectrometer entry to master.** Since **Acquisition now contains only the Virtual
  Spectrometer button**, the simplest gate is to make the **Acquisition section master-only** — add
  `self.acquisitionSettingsGroupBox` to `updateAdministrationVisibility()` (keep a reference to it in
  `__init__`, currently a local). *(Alternative: move the button into the existing master-only
  **Administration** section and delete the empty Acquisition section — a bit more churn; pick at impl.)*
- **Defense in depth (recommended, cheap):** in `VirtualSpectrometerViewModule`, on `showEvent` (or before
  the folder load) refuse a non-master — hide/disable "Set image folder…" and show a short "Master only"
  note — so the screen is safe even if reached some other way (mirrors `UserListViewModule.refresh()`'s
  role check).

### 3.4 Nuance (not a blocker) — fileset persistence
`VirtualSpectrometerSettings` holds the images **in-memory** (not persisted). They survive a
**logout→login within one app run** (so the master→end-user workflow works in a session), but are **lost
on app restart** — the master must re-set the fileset each launch. Out of scope here; may later motivate
persisting the fileset (own task).

## 4. Implementation phases (when requested)

```
 ID   Item  File(s) touched                                Change                                       Depends on
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 P1   B     VirtualSpectrometerViewModule.py               Delete the save-images row (l.34) + its       —  (independent)
                                                           getter (41-46), handler (72-78) and the
                                                           duplicate field decl (l.18/21).
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 P2   A     HomeViewModule.py                              Remove settingsButton (69-72) +               —
             + MainStatusBarViewModule.py                   onClickedSettingsButton (31-35); ADD a
                                                           "Settings" QAction to the logged-in desktop
                                                           account menu -> nav SettingsViewModule.
                                                           BOTH edits in one change (RD1).
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 P3   C     SettingsViewModule.py                          Store acquisitionSettingsGroupBox on self;
             + VirtualSpectrometerViewModule.py             add it to updateAdministrationVisibility()
                                                           (master-only). Optional: showEvent role
                                                           guard on the screen (defense in depth).
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 P4   —     (run the app)                                  VERIFY: Home footer clean (no empty band);    P1+P2+P3
                                                           Settings in the account menu when logged in;
                                                           end user does NOT see Virtual Spectrometer /
                                                           cannot set the fileset; master does; save-
                                                           images row gone; app starts clean.
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 (deferred, M4)  Android account menu — see §1.5 (verify QMenu crash claim first; in-window page only if needed).
```

P1/P2/P3 are independent (no ordering constraint between them); P4 verifies the union. Buildable now:
all of P1–P3 (desktop). Android (§1.5) is out of scope.

## 5. Rubber-duck review

Adversarial read against the actual code. ✅ = folded in; ◻ = accepted impl-time tune.

| # | Finding | Resolution |
|---|---------|-----------|
| RD1 | **Orphan window.** Removing the Home button and adding the menu entry in *separate* steps leaves Settings unreachable in between. | ✅ §1.4/P2: do both edits in **one** change. |
| RD2 | **`acquisitionSettingsGroupBox` is a local**, not `self.` (SettingsViewModule.py:35) — `updateAdministrationVisibility()` can't toggle it. | ✅ §3.3/P3 explicitly stores it on `self` first. |
| RD3 | **End-user Settings becomes very sparse.** With Administration/Development already master-only and Acquisition now master-only too, a logged-in **end user** sees only **Downloads** (a placeholder) + **Infos** (About/Help). | ◻ Acceptable — About/Help is a fine reason to keep it. If it reads as empty, a later call could hide Settings for end users entirely. Flagged, not changed. |
| RD4 | **Gate placement choice.** Gating the whole *Acquisition* section vs. moving the button into *Administration*. | ◻ Both correct; §3.3 recommends gating in place, notes the move alternative. Pick at impl. |
| RD5 | **Footer re-flow.** After dropping the col-3 button, does the grid leave an empty stretched column? | ◻ `createNavigationGroupBox` sets **no** `setColumnStretch`, so col 3 with no widget takes no space; 3 buttons left-pack as before. Verify visually in P4. |
| RD6 | **Menu-item order** — where "Settings" sits relative to "Account settings…" / "Logout". | ◻ Impl choice; suggest `… (header) · ─ · Account settings… · Settings · ─ · Logout`, so Logout stays visually separated. |
| RD7 | **Dead setter after Item B.** Leaving `set/getDoSavePhysicallyCapturedImages` + the `VideoThread` branch means the setter is now unused. | ◻ Harmless (default `False` path unchanged); the "thorough cleanup" option (§2.3) can remove it later. |
| RD8 | **Defense-in-depth timing.** A role check must run when the screen is *navigated to*, not at construction (built once at startup while logged out). | ✅ §3.3 puts it on `showEvent`, not `__init__` (mirrors `UserListViewModule`). |
| RD9 | **`updateAdministrationVisibility` at construction** hides Acquisition while logged out — correct, but confirm it re-shows for a master on `userSessionSignal` (it already drives Administration/Development the same way). | ✅ Same signal path; adding Acquisition to it inherits the behaviour. |

**Verdict:** low-risk, all desktop, all three items grounded in the code. The one real trap (RD2, the
local group-box reference) is called out. RD3 (thin end-user Settings) is the only thing worth an eye
after it ships. **Ready to build on request.**

## 6. As-built (2026-07-06)

Built P1–P3 on explicit request ("build P1-P3"). Desktop only; Android (§1.5) untouched.

### 6.1 Changes
- **Item A** — `HomeViewModule.py`: removed `settingsButton` + `onClickedSettingsButton` (footer now
  `New measurement` / `Edit` / `Delete`). `MainStatusBarViewModule.py`: added a **"Settings"** action to
  the logged-in desktop account menu (`… (header) · ─ · Account settings… · Settings · ─ · Logout`) →
  navigates to `SettingsViewModule`. Refactored the connect/emit into a `__navigateTo(target)` helper
  reused by the login navigation and both menu actions.
- **Item B** — `VirtualSpectrometerViewModule.py`: removed the "save physically captured images" row,
  its getter, its state-change handler, the duplicate field decl, and the now-unused `Qt` /
  `ToggleSwitch` / `ApplicationStyleLogicModule` imports. Model field + `VideoThread` branch left as-is
  (default `False`); the setter is now unused (thorough cleanup deferred per §2.3).
- **Item C** — `SettingsViewModule.py`: `acquisitionSettingsGroupBox` stored on `self` and added to
  `updateAdministrationVisibility()` → master-only. `VirtualSpectrometerViewModule.py`: `showEvent`
  role guard (defense in depth) — non-master gets the picker disabled + a "master only" note.

### 6.2 Verified (offscreen)
- `py_compile` clean (4 files); full app launches offscreen with **no tracebacks**.
- **A:** Home footer buttons = `New measurement / Edit / Delete` (no Settings); handler removed.
- **C:** Acquisition section hidden for logged-out **and** end-user, visible for master (alongside
  Administration/Development).
- **B + C guard:** Virtual-spectrometer screen builds without the row; `showEvent` enables the picker +
  hides the note for a master, disables the picker + shows the note for an end user.
- **Not covered:** the live desktop `QMenu` "Settings" click (menu popup isn't offscreen-testable) —
  Edwin's click-through.

### 6.3 Click-through — PASSED (Edwin, 2026-07-06)
Verified in the running desktop app: master sees **Account settings… / Settings / Logout** and can open
Settings → Virtual Spectrometer → set the fileset; end user has **Settings** but no Virtual Spectrometer
section; Home footer has no Settings button. All three items behave as designed.

---
*P1–P3 implemented (desktop) + offscreen-verified + click-through verified. Android account-menu handling
deferred (§1.5). Item B thorough cleanup (dead setter) optional (§2.3).*
