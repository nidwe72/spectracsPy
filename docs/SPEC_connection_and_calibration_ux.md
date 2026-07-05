# Spec — Connection & calibration UX (serial-keyed setup, master authoring, end-user self-registration)

Status: **DESIGN.** Not implemented — spec-first, build on explicit request only. Companion to
`SPEC_real_camera_capture.md` (the physical capture path); this spec covers the **integration layer** above
it: who sets up an instrument, how an end user activates it, and how the app knows a real, calibrated
spectrometer is connected before a measurement. Seeded from `SPEC_real_camera_capture.md` §9.1/§9.4 — that
file remains the record of how these decisions were reached; **this spec is authoritative going forward.**

Goal: a coherent, end-user-sensible setup where the **serial** printed on the hand-held unit is the pivot
key. A **master** authors, per serial, the `{ device, calibration, plugin }` bundle; an **end user
self-registers** by entering that serial; the app then **resolves the live USB camera, shows it is
connected, and drives a real measurement** (live-during-burst → spectrum graph).

---

## 0. Why this shape (the problem it solves)

Today two halves live on two disconnected sides, in **two separate databases**:
- **Per-user (server DB):** `AppUser.pluginId` (FK→`DbPlugin`) + `AppUser.spectrometerDevice` (soft
  code-name string, e.g. `"Virtuax"`), set at **seed only**.
- **Global (app DB):** `ApplicationConfig` (single row) → `ApplicationConfigToSpectrometerProfile.isDefault`
  → `SpectrometerProfile.serial` → `SpectrometerCalibrationProfile` (ROI + pixel→nm cubic).

So "which plugin/user" and "which calibrated profile is active" are decided on two unconnected sides that
cannot even FK to each other. Decision **D15** (`SPEC_pumpkin_integration.md`) bound the device by a soft
code-name string precisely because profile `uuid4` ids are random per-client and a seeded profile id would
**dangle**.

**The serial dissolves this.** `SpectrometerProfile.serial` is a **stable, human-assigned natural key**,
printed on the unit's label, identical on the master side and the end-user side. Keying on the serial makes
both halves meet on one key and removes the D15 dangling-id workaround. The `RegisterSpectrometerProfile`
screen already tells the user this is how it works: *"Your spectrometer has been calibrated in the factory.
Please supply the serial number of the device for downloading the calibration profile."*

**Note — serial vs login identity.** The serial keys the **instrument bundle**, not authentication. The end
user still logs in with their own **credentials**; the serial links *that user* to *their instrument* at
registration. (Login identifier at registration is an open item — §7.)

---

## 1. Current state (as-is, code-verified)

| Area | As-is | File |
|---|---|---|
| Two databases | Server DB (`AppUser`, roles, `DbPlugin`); App DB (`ApplicationConfig`, `SpectrometerProfile`, `Spectrometer`, `Sensor`, `SpectrometerCalibrationProfile`). No cross-DB FK. | `DbServerBase.py`, `DbBase.py` |
| AppUser | `username` (unique, immutable), `passwordHash`, `displayName`, `enabled`, `pluginId` (FK→`DbPlugin`), `spectrometerDevice` (string). | `.../application/user/AppUser.py` |
| Roles | `AppUserRole`(name) + `AppUserToAppUserRole` join; enum `END_USER`/`MASTER_USER`. | `.../user/UserRoleType.py` |
| Plugin binding | Per-user `AppUser.pluginId`; set at **seed only** (`UserSeedLogicModule`); read at login (`LoginLogicModule` returns `pluginCodeRef`); cached transiently in `CurrentUserSession`. | `LoginLogicModule.py:24-27`, `CurrentUserSession.py:20-30` |
| Serial-object editor (master) | **Exists**: edits serial + `Spectrometer` (device) + embedded `SpectrometerCalibrationProfileViewModule`. **Missing: plugin field.** | `SpectrometerProfileViewModule.py:174-189` |
| Calibration profile | ROI (`x1/y1/x2/y2`) + pixel→nm cubic (`interpolationCoefficientA..D`) + `spectralLines`. No back-FK to sensor. | `.../calibration/SpectrometerCalibrationProfile.py` |
| Device model | `Spectrometer` = model (modelName + sensor + vendor + style); `Spectrometer.id` referenced by **only** `SpectrometerProfile.spectrometerId`; a `getSpectrometers()` server RPC already exists. | `Spectrometer.py`, `SpectracsPyServerClient.py:126` |
| End-user register-by-serial | **Exists but thin**: types serial → looks up profile → appends to **global** `ApplicationConfig`. No account creation, no plugin/session resolution. | `RegisterSpectrometerProfileViewModule.py:71-97` |
| Master user admin | **Exists**, role-gated: `UserListViewModule`/`UserViewModule` (username/displayName/password/role/enabled). No plugin/device field. | `UserViewModule.py:37-62` |
| Connect button | **Exists but misleading**: only picks a stored profile (combo); no hardware handshake, never calls `isSensorConnected`. | `SettingsViewModule.py:69`, `SpectrometerConnectionViewModule.py` |
| Connection status | **Weak**: only a text suffix `" (not connected)"` on the profile editor; `getSpectrometersHavingSensorConnected()` is dead code; no icon/badge. | `SpectrometerProfileViewModule.py:82-84` |
| Live preview | Calibration bursts + legacy `SpectralJob` show frames **during** a capture burst; the new Wizard has **none**. | `SpectralJobWidgetViewModule.py:56-92`, `WizardViewModule.py:248-278` |

---

## 2. Roles

- **MASTER user** — authors instruments. Creates/edits the **serial-keyed setup object**
  (`SpectrometerProfile`): assigns the **serial**, picks the **`Spectrometer` model** (→ sensor/chipset),
  produces the **calibration profile** by calibrating against the **CFL** lamp, and assigns the **plugin**.
  Retains the existing **User admin** (`UserViewModule`) for master-only data the master alone may
  edit/inspect — but the master does **not** create end-user accounts.
- **END user** — self-registers (creates own account + enters the serial), then measures. Cannot author
  instruments.

---

## 3. Target object model

### 3.1 Decisions (LOCKED, 2026-07-05)
1. **Key on serial, not username.** (Reverses Roadmap #3's "select an `AppUser`" and the "username = future
   serial" idea.)
2. **Server-authoritative.** The whole coherent device graph moves to the **server DB**:
   `Spectrometer` / `SpectrometerSensor` / `SpectrometerSensorChip` (catalog) **+** `SpectrometerProfile`
   (item) **+** `SpectrometerCalibrationProfile` (calibration). FKs stay intra-DB; the client fetches by
   serial.
3. **Session-resolve, not persistent cache.** The bundle is resolved at login/registration into
   `CurrentUserSession` (like `pluginCodeRef` today); a persistent local copy is optional/deferred — the
   product is **online-required** anyway (LIMS + licence check, §6).
4. **`AppUser` slims to identity + role.** Drop `pluginId`/`spectrometerDevice`; everything resolves through
   the registered serial. Add a **`AppUser ⇄ serial`** link — **one user ⇄ one serial** for now.
5. **Registration captures** **username** (the login id, as today) + **password** + **email (mandatory,** for
   support/feedback mailing**)** + **first + last name** + **serial**.
6. **Serial = a short typable code `XXXX-XXXX`** (Edwin) — 8 alphanumeric chars in two dash-separated groups,
   master-generated and unique, printed on the unit's label. Short enough to hand-type (no QR needed); ample
   key space (~36⁸ ≈ 2.8×10¹² if `[0-9A-Z]`). *(Supersedes the earlier "standard GUID" idea.)*
7. **A parent object `SpectrometerSetup` holds the plugin — CONFIRMED (Edwin).**
   Rather than a `pluginId` FK directly on `SpectrometerProfile`, a parent
   **`SpectrometerSetup`** (server-DB) references **`SpectrometerProfile` + `DbPlugin`**. Rationale:
   separates **calibrated hardware identity** (the profile = serial + device + calibration, factory truth)
   from **deployment/assignment** (which plugin the unit runs) — the plugin can change without touching the
   calibration, and `SpectrometerSetup` becomes the natural home for later commercial refs (licence, owner,
   LIMS config). `AppUser.registeredSerial` → `SpectrometerProfile` (by serial) → its `SpectrometerSetup` →
   plugin.
8. **Full server-DB migration up-front (Edwin)** — do the complete object-model move (decision 2 +
   `SpectrometerSetup` + `AppUser` changes) as the **first build step**, not a leaner in-place slice.
9. **Build order (Edwin): (1) `CX-DB` full migration → (2) master-user GUIs → (3) end-user GUIs**, with
   **connect** part of this first sweep (§4.4). Three master GUIs — Plugin, SpectrometerProfile,
   SpectrometerSetup (§4.1); the `SpectrometerProfile` GUI **auto-calibrates in the background** when a virtual
   file-set containing a calibration image is assigned (§4.1.b).

### 3.2 Target graph

```
  SERVER DB
  ┌─────────────────────────────────────────────────────────────────────┐
  │  AppUser                                                             │
  │    • username (login id)  • passwordHash  • email (mandatory)        │
  │    • firstName • lastName • enabled                                  │
  │    • registeredSerial ──────────────┐  (1:1 for now)                 │
  │    └─< AppUserToAppUserRole >─ AppUserRole (END_USER | MASTER_USER)  │
  │                                     │                                │
  │  SpectrometerSetup  (parent — deployment/assignment)                │
  │    • spectrometerProfileId ─FK─► SpectrometerProfile                 │
  │    • pluginId ─FK─► DbPlugin (title, codeRef, version, pdfRef)       │
  │    • (later: licence, owner, LIMS config)                           │
  │            │                                                        │
  │  SpectrometerProfile  ◄── keyed by  ┘ serial (XXXX-XXXX)            │
  │    • serial (XXXX-XXXX alphanumeric, on label — the natural key)    │
  │    • spectrometerId ─FK─► Spectrometer                               │
  │    • spectrometerCalibrationProfileId ─FK─► SpectrometerCalibrationProfile
  │                                                                     │
  │  Spectrometer (MODEL) ─FK─► SpectrometerSensor ─FK─► ...Chip         │
  │  SpectrometerCalibrationProfile (ROI + pixel→nm cubic + SpectralLine)│
  └─────────────────────────────────────────────────────────────────────┘
                    │  resolve-by-serial RPC (at login / registration)
                    ▼
  CLIENT (app)  — CurrentUserSession (transient): loginId, roles,
                  serial, pluginCodeRef, device code-name, ROI + pixel→nm coeffs
                  (App DB keeps only local settings / optional cache)
```

### 3.3 Migration from current
- **Move** `Spectrometer`/`Sensor`/`Chip`, `SpectrometerProfile`, `SpectrometerCalibrationProfile` from app
  DB → server DB (base class `DbBaseEntity` → `ServerDbBaseEntity`). *(The `getSpectrometers()` RPC shows
  this was anticipated.)*
- **Add** new entity **`SpectrometerSetup`** (server-DB) with FKs → `SpectrometerProfile` + `DbPlugin` (§3.1-7);
  **add** `AppUser.registeredSerial` + `AppUser.email` (+ `firstName`/`lastName`); **remove**
  `AppUser.pluginId` + `AppUser.spectrometerDevice`. *(Plugin FK lives on `SpectrometerSetup`, not on
  `SpectrometerProfile`.)*
- **Retire/repurpose** `ApplicationConfig`/`ApplicationConfigToSpectrometerProfile` (the global
  active-profile mechanism) — active instrument now = the logged-in user's `registeredSerial`.
- **New RPCs** (server): **public** — `resolveInstrumentBySerial(serial)` → bundle,
  `registerEndUser(username, password, email, firstName, lastName, serial)`; **master (role-gated)** — plugin
  CRUD (`listPlugins`/`savePlugin`), `saveSpectrometerProfile`, `saveSpectrometerSetup`,
  `listSpectrometerProfiles`/`Setups`. Existing `login()` extends to return the resolved bundle. (Full phase
  breakdown in §9.)

---

## 4. Flows

### 4.1 Master — author an instrument (THREE master screens, Edwin)

Setup is split across **three master GUIs**, not one embedded selector:

**4.1.a Plugin management GUI (NEW).** CRUD over `DbPlugin` (fields: `title`, `codeRef`, `version`,
`pdfRef`). The `PumpkinOilPlugin` **class** already exists and a `DbPlugin` row is seeded via
`getOrCreate`, but **there is no GUI** to view/add/edit plugins — build one. This is the catalog the
`SpectrometerSetup` screen picks from.

**4.1.b SpectrometerProfile GUI (mostly exists).** `SpectrometerProfileViewModule` already edits **serial +
`Spectrometer` (device) + embedded calibration**. Change: **auto-calibrate on file-set assignment (M2,
Edwin)** — when the master assigns a **virtual capture file-set** to the profile and that set contains a
**calibration image**, calibration runs **in the background** and the resulting ROI + pixel→nm coefficients
are **written to the DB** (no manual calibration step for the virtual path). *(This mirrors what
`SpectralWorkflowEngine` already does auto-calibrating from `calibration.png`.)*

**4.1.c SpectrometerSetup GUI (NEW).** The parent object: bind a **`SpectrometerProfile`** to a **plugin**
(from 4.1.a). This is where `serial → { profile (device + calibration), plugin }` is assembled and saved
server-side.

**Calibration authoring already largely exists (verified — resolves old §7-Q2).** The wiring is in place:
- Hough ROI → `SpectrometerCalibrationProfileHoughLinesViewModule.handleVideoThreadSignal` writes
  `model.regionOfInterestX1/X2/Y1/Y2` (`:178-184`) from the detected bounding lines.
- Wavelength → `SpectrometerCalibrationProfileWavelengthCalibrationViewModule.handleWavelengthCalibrationVideoSignal`
  (`:155`); the video thread computes `interpolationCoefficientA..D` onto the shared model.
- Save → `SpectrometerCalibrationProfileViewModule.onClickedSaveButton` →
  `PersistSpectrometerCalibrationProfileLogicModule().saveSpectrometerCalibrationProfile(model)` (`:113`),
  and the calibration editor is embedded in the `SpectrometerProfile` editor.
So the master-authoring **deltas** are: **(a)** new **Plugin management GUI** (4.1.a); **(b)** new
**SpectrometerSetup GUI** (4.1.c); **(c)** **auto-calibrate on file-set assignment** (4.1.b); **(d)** repoint
persistence from the **app DB** to the **server DB** (per §3.1-2). The virtual path needs none of the real
camera; calibrating against the **CFL on the real camera** is the later 5b step (depends on RC-R2).

### 4.2 End user — self-register
**New** registration view module, reached via a **"Register" link on the login screen** (E1, Edwin). Captures
**username, password, email, first + last name, serial** (§3.1-5). On submit → `registerEndUser(...)`:
- **Serial validation (E2):** the serial must resolve to a master-authored `SpectrometerSetup`. If it does
  **not**, show the existing **factory-calibration message** — *"Your spectrometer has been calibrated in the
  factory…"* — worded as **the calibration could not be downloaded** (i.e. no setup exists for this serial).
  Also enforce **1:1** (serial not already registered to another user).
- **Username** must be unique → error if taken. **No email verification** for the milestone (E3).
- On success: create the `AppUser` (role `END_USER`, `registeredSerial = serial`), resolve the bundle, and
  **auto-login** into Home (E1 — "auto-login" = the app signs the new user in immediately rather than
  bouncing them back to the login screen to type their credentials again).

Distinct from today's `RegisterSpectrometerProfileViewModule` (which only appends to global config, no
account).

### 4.3 Login / session resolve
`login()` (or the tail of registration) resolves the user's `registeredSerial` → the `{ device (code-name),
calibration (ROI + coeffs), pluginCodeRef }` bundle → `CurrentUserSession`. Online-required; the **licence
check** (§6) is a natural gate at this step.

### 4.4 Connect + connection status  **(part of the FIRST sweep, Edwin)**
Connecting to the spectrometer is **included in milestone 5a** (not deferred with real capture). Replace the
misleading "Connect spectrometer" combo with a real check + a **clear connected / not-connected indicator**
(icon/badge, not just a text suffix).

**Autoconnect by USB enumeration (Edwin) — the device info is already in the templates.** The USB
**VID/PID lives on the hard-coded `SpectrometerSensor` templates** (`SpectrometerSensorUtil.getSpectrometerSensors()`:
`vendorId`/`modelId` — virtual `0c99/9999`, Microdia `0c45/6366`, ELP `32e4/8830`), and the enumerate-match is
**already written but dead**: `ApplicationSpectrometerUtil.isSensorConnected()` (`usb.core.find(idVendor,
idProduct)`) and `getSpectrometersHavingSensorConnected()` (no callers → **revive it**). Two flavours:
- **Targeted (recommended for end-user autoconnect):** the logged-in user's serial → bundle already names the
  device, so verify **that** sensor's VID/PID is present — no multi-camera ambiguity.
- **Enumerate-and-match** (`getSpectrometersHavingSensorConnected`): find *any* known spectrometer — for the
  master/setup screen or when there is no session.

**Three build caveats:**
1. **Virtual (5a) has no USB presence** (`0c99/9999` isn't on the bus) → 5a "connect" is a **software check**
   (virtual is always connected). USB enumeration is the **5b (real-device)** mechanism.
2. **Present ≠ capturable** — `usb.core.find` only proves it is plugged in; actually opening it needs the
   **RC-R0 resolver** (VID/PID → cv2 index). Real autoconnect = *present* **and** *resolvable*; the
   `-71`/`select timeout` "device present but no frames" is a distinct status.
3. **pyusb is desktop-only** (Android deferred), per the capture spec.

Status states to distinguish: "no device" / "device present but no frames" / "connected".

### 4.5 Measurement UX
Adopt the legacy pattern (decided): during the 20/50-frame burst show the **live camera image**; afterwards
show the **captured spectrum as a graph**. The new `WizardViewModule` (currently Measure-button + static
plot) must gain the live-during-burst view.

---

## 5. Milestones — virtual-first, then real device

**Priority (Edwin, 2026-07-05):** build this setup/registration flow **first, against the VIRTUAL
spectrometer** — the virtual-device functionality already exists, so no real camera is needed. Real capture
(`SPEC_real_camera_capture.md`, RC-R0…R3) is **postponed**. This splits the goal into two milestones:

### 5a. MILESTONE (first sweep) — setup + registration + connect + measurement on the **virtual** device
1. **Master** (`masterUser`) logs in and, across the **three master GUIs**, authors an instrument:
   **Plugin** GUI (4.1.a) → **SpectrometerProfile** GUI (4.1.b; assigning a virtual file-set with a
   calibration image **auto-calibrates in the background** → DB) → **SpectrometerSetup** GUI (4.1.c; bind
   profile + plugin). Result: `serial (XXXX-XXXX) → { device, calibration, plugin }`, saved server-side. **No
   real CFL capture.**
2. **A new end user self-registers** (username + password + email + first/last name) via the login-screen
   **Register** link and **enters the serial** → bundle resolved into the session → **auto-login**.
3. **Connect** to the spectrometer (§4.4) — for the virtual device a software check; connection status shown.
4. The end user runs a measurement on the **virtual spectrometer** (existing acquisition) → plugin evaluation
   renders.

Depends only on **CX-DB → CX-M → CX-E (+ connect)** — **no capture-track dependency**.
**Build order (Edwin): (1) full DB migration `CX-DB`, (2) master-user stuff, (3) end-user stuff** (connect is
part of this sweep). This is the first **GUI-testable unit**.

### 5b. MILESTONE (later) — the same, on the **real** device
As 5a but the master calibrates against the **CFL** on the real ELP camera and the end user measures on real
hardware (live-during-burst → spectrum graph). Adds dependency on capture track **RC-R2/RC-R3**.

---

## 6. Commercial / integration constraints (context; detailed design deferred)

- **Online-required.** Normal operation assumes connectivity (these two constraints are why local caching is
  optional, not required).
- **LIMS integration** *(deferred)* — push results / pull sample context to a lab information management
  system.
- **Rental-fee / licensing gate** *(deferred)* — a monthly rental-fee / licence check gates use; the
  natural hook is the resolve-by-serial / login step (§4.3).

---

## 7. Open / resolved questions

- **RESOLVED — Login identifier (Edwin):** login is by **username** (as today); **email is a mandatory**
  additional field (for support/feedback mailing). Registration = username + password + email + first/last
  name + serial (§3.1-5).
- **RESOLVED — Calibration authoring persistence (verified in code):** the Hough + wavelength flows **do**
  write ROI + pixel→nm coefficients (+ spectral lines) into the `SpectrometerCalibrationProfile` and persist
  it (§4.1). Remaining deltas are only the plugin selector + server-side persistence.
- **RESOLVED — Serial format (Edwin):** a short **`XXXX-XXXX`** alphanumeric code (not a full GUID),
  master-generated + unique, printed on the label; hand-typable (§3.1-6).
- **RESOLVED — parent object `SpectrometerSetup` CONFIRMED (Edwin):** plugin lives on the parent, not on the
  profile (§3.1-7).
- **RESOLVED — First-master provisioning: already seeded (keep).** `UserSeedLogicModule` **already seeds
  `masterUser/masterUser`** with role `MASTER_USER` (`:20`) — keep it. Thereafter masters are managed through
  the retained master **User admin** (`UserViewModule`). End-user self-registration always produces role
  `END_USER` only.
- **Open (deferred with §6) — Licence-check contract** — what the resolve-by-serial step verifies and how it
  fails closed.

---

## 8. Cross-references
- `SPEC_real_camera_capture.md` — physical capture path (§2.1 resolver, §7 decisions, §9 threads) that this
  spec's connection/measurement steps sit on top of.
- `SPEC_pumpkin_integration.md` — current `AppUser → {Plugin, device}` binding + decision D15 (which the
  serial key supersedes).
- `SPEC_user_crud.md` / `SPEC_user_auth_login.md` — current user CRUD + auth (the "username = future serial"
  idea, now superseded).
- `spectracs-docs/ROADMAP.md` — item #3 (direction-changed to serial-keyed) + the "Real-hardware capture &
  connection/calibration" section (this spec = the `CX` design step).
- `KB_spectroscopy_physics.md` §7 — hardware construction (hand-held grating-on-lens; CFL vs LED sources).

---

## 9. Implementation phases — sub-milestone 5a (virtual, GUI-testable)

Build order (Edwin): **DB migration → master GUIs → end-user + connect.** All on the virtual device; no
capture-track dependency.

```
 PH  STEP   WHAT                                                DEPENDS   KEY TOUCHPOINTS / NOTES
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
 A   CX-DB — the load-bearing wall (full migration up-front)
 A1  entities   +SpectrometerSetup(→Profile,→DbPlugin);        —         AppUser.py, new SpectrometerSetup.py
                AppUser +registeredSerial/email/first/last,
                −pluginId/−spectrometerDevice
 A2  move       device graph app-DB→server-DB (base class      A1        Spectrometer/Sensor/Chip/Vendor/Style,
                DbBaseEntity→ServerDbBaseEntity) + re-seed                Profile, CalibrationProfile, SpectralLine;
                catalog server-side (dev: re-seed, no data mig)          Persist* modules move server-side
 A3  RPCs       public: registerEndUser, resolveInstrumentBySerial;  A2  extend LoginLogicModule dict with bundle;
                master: plugin CRUD, saveProfile, saveSetup,             new @expose on the Pyro daemon
                listProfiles/Setups; extend login()→bundle
 A4  repoint    client DB reads → RPC/session; RETIRE            A3       ImageSpectrumAcquisition reads calib
                ApplicationConfig.isDefault active-profile;              from SESSION (not per-frame RPC);
                acquisition reads calib from session bundle              applicationSettings.getSpectrometerProfile()
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
 B   MASTER GUIs (role-gated MASTER_USER)
 B1  plugin     NEW Plugin management GUI = DbPlugin CRUD        A3       title/codeRef/version/pdfRef; catalog
                (title, codeRef, …)                                      the Setup screen picks from
 B2  profile    SpectrometerProfile GUI → server persistence    A3,B?    reuse SpectrometerProfileViewModule;
                + AUTO-CALIBRATE on file-set assignment (bg)             Hough/λ compute client → save server
 B3  setup      NEW SpectrometerSetup GUI = bind Profile+plugin B1,B2    assembles serial→{profile,plugin}
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
 C   END-USER + CONNECT
 C1  register   Register link on login → self-register form →   A3,B3    registerEndUser (PUBLIC rpc); validate
                validate serial → create AppUser → auto-login            serial→Setup else factory-cal message
 C2  resolve    login/register resolves bundle into session     A3,C1    CurrentUserSession holds ROI+coeffs+
                                                                         pluginCodeRef+device
 C3  connect    revive isSensorConnected /                      A2       virtual = software "connected"; real =
                getSpectrometersHavingSensorConnected;                   5b (USB enum + RC-R0 resolver)
                status indicator (icon/badge)
 C4  measure    end-user measures on VIRTUAL (existing folder   B2,C2,C3 sample image via existing virtual
                picker for sample img) → plugin eval  ⇒ 5a done          folder picker; calib+plugin from bundle
```

### 9.1 Migration notes / risks (rubber-duck)
- **Real schema move, not a reseed.** The catalog is persisted (`PersistSpectrometerSensor/Spectrometer`),
  so moving to server-DB means **every client read becomes an RPC**. Dev has no production rows → re-seed
  server-side rather than data-migrate.
- **Acquisition must read calibration from the SESSION, never per-frame RPC** — the a2 session-resolve
  decision is what makes the server-DB move viable.
- **Calibration: compute client-side, store server-side** — the Hough/λ image processing stays on the client
  (runs on the assigned file-set's calibration image); only the ROI+coeffs result is persisted via RPC.
- **`registerEndUser` is a PUBLIC RPC** (pre-login, no session/role) — unlike the role-gated master RPCs.
- **Retiring `ApplicationConfig.isDefault`** must repoint the pumpkin read path
  (`applicationSettings.getSpectrometerProfile()`) to the session bundle, or virtual measurement breaks.
- **5a sample image** comes from the existing `VirtualSpectrometerViewModule` folder picker (client-side);
  the bundle ships calibration+plugin, not image blobs.
