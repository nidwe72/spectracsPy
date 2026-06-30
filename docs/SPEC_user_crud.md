# SPEC — User CRUD (master-user admin screen)

> **Roadmap item #4.** Status: **IMPLEMENTED 2026-06-30** (all 6 phases §13). Verified: 11 façade
> functional checks (rules + last-master guard, hash never leaks), UI instantiation offscreen
> (create/edit modes, role-gated Administration group, table columns), and a live Pyro round-trip
> (`listUsers`/`createUser`/`deleteUser`).
>
> **Post-impl fix (2026-06-30):** click-through review found the list froze on its startup
> (logged-out) state because `refresh()` ran only at build time + on `userSignal`. Fixed by
> re-fetching in `showEvent` (every navigation re-evaluates the role gate + reloads users); also
> hid the `QTableView` vertical-header gutter. Re-verified by driving login→navigate (3 rows) and
> logout→revisit (back to "Not authorized").
>
> **Layout fix (2026-06-30):** the editor's 5 fields spread over the panel height (looked broken) and
> the Enabled `QCheckBox` rendered as a big green box (it inherits the themed button fill). Fixed with
> a new `PageWidget.compactMainContainer` mode (fields pack at top), a global QSS reset of
> checkbox/radio backgrounds to transparent, and a compact wrapped checkbox.
>
> **Styling (2026-06-30):** fixed the login button's native blue default-frame (`QAbstractButton`
> `border:none`); added Bootstrap-style button variants
> (`setProperty("buttonType", "secondary"|"info"|"danger")`). Cancel and the user-table **Delete** are
> `secondary` (gray) — Delete stays guarded by its confirm dialog; `info` is a light-gray placeholder.
>
> All cosmetic fixes were found and re-verified by **click-through review** (drive the running app,
> screenshot each step) — see `docs/DEV_WORKFLOW.md`; UI patterns captured in `docs/DESIGN_GUIDE.md`.
> Original design below.
> Builds directly on the Step-2 auth plumbing (`SPEC_user_auth_login.md`) and the header login
> control (`SPEC_login_header_placement.md`). This is the *user-admin UI* that Step 2 explicitly
> deferred ("a full user-admin / serial-publishing UI (only a bootstrap master here)").
>
> Scope is **user CRUD only**. The `AppUser ↔ SpectrometerProfile` binding is **Roadmap #3** and is
> out of scope here — but the entities and RPCs below are shaped so #3 plugs in without rework.

---

## 1. Goal

A **master user** can manage application users from inside the app:

- **List** all users (username, display name, role(s), enabled).
- **Add** a user (username, display name, password, role, enabled).
- **Edit** a user (display name, role, enabled; optional password reset).
- **Delete** a user.

This feeds Roadmap #3 ("select an `AppUser`" when binding a `SpectrometerProfile`) and the master/
end-user role gate (Step-2 phase G), making this screen the **first real consumer** of
`CurrentUserSession().hasRole(...)`.

## 2. Non-goals (deferred — do not build here)

- `AppUser ↔ SpectrometerProfile` link / serial-publishing (**Roadmap #3**).
- Session tokens / per-RPC authorization (Step-2 decision #9 — still deferred). These CRUD RPCs are,
  for now, **unauthenticated at the transport layer**, exactly like `login` today. The *UI* gates on
  role; the server does not yet. Flagged as a known gap (see §9).
- TLS (Step-2 phase D).
- Password-reset-by-email, lockout / rate-limiting, self-registration, audit log.

## 3. What already exists (recap — reuse, don't rebuild)

**Model layer (`spectracsPy-model`):**
- `AppUser(username unique, passwordHash, displayName, enabled)` — server DB, UUID PK from
  `DbBaseEntityMixin`.
- `AppUserRole(name unique)`, `AppUserToAppUserRole(app_user_id, app_user_role_id)` composite-PK join.
- `UserRoleType` enum = `END_USER`, `MASTER_USER` (single source of truth).
- `PasswordUtil.hash()/verify()` (bcrypt, server-side only).
- `PersistUserLogicModule` — has `findUserByUsername`, `findRoleByName`, `getRoleNamesForUser`,
  `saveUser`, `saveRole`, `saveUserToRole`. **No `findById`, `listAll`, `update`, `delete`,
  `replaceRoles` yet.**
- `UserSeedLogicModule.seed()` (idempotent; two dev users) — run at server `__init__`.

**Server (`spectracsPy-server`):** `SpectracsPyServer` exposes only `@expose login(...)`. **No user-CRUD
RPCs.**

**Client (`spectracsPy`):** `SpectracsPyServerClient.login()` is the only user RPC; returns a plain
hash-free dict, never raises. `CurrentUserSession` (singleton, in-memory). `userSessionSignal` on
`ApplicationSignalsProviderLogicModule`. `PageWidget` list/edit template; navigation via string-target
`NavigationSignal` + `NavigationHandlerLogicModule` + `MainViewModule` index registration.

## 4. Cross-Pyro DTO contract

Mirror the `login` convention exactly: **plain dicts / lists of dicts, never ORM entities, never
`passwordHash`.**

**User DTO** (read shape, returned by list/get):
```python
{ "userId": str, "username": str, "displayName": str|None,
  "enabled": bool, "roles": [str, ...] }     # roles = UserRoleType values
```

**Mutation result** (returned by create/update/delete):
```python
{ "ok": bool, "userId": str|None, "message": str|None }
```
`message` carries the human-readable reason on `ok=False` (e.g. `"username already exists"`,
`"cannot delete the last master user"`). On `ok=False`, `userId` is `None`.

Password only ever travels **client → server** (plaintext over the wire today — same as `login`;
TLS is phase D). It is **never** returned.

## 5. Model-layer changes (`spectracsPy-model`)

### 5.1 `PersistUserLogicModule` — add methods (same `server_session_factory()` + `commit()` idiom)
- `findUserById(userId) -> Optional[AppUser]`
- `listAllUsers() -> List[AppUser]`
- `updateUser(appUser)` — `session.merge` + commit (id already set).
- `deleteUser(userId)` — delete the `AppUser` **and** its `AppUserToAppUserRole` link rows.
- `replaceUserRoles(appUser, roleNames: List[str])` — delete existing links for the user, re-create
  links for the given role names (look each up via `findRoleByName`).
- `countUsersWithRole(roleName) -> int` — for the "last master user" guard.

### 5.2 New `UserAdminLogicModule` (`logic/user/UserAdminLogicModule.py`)
The business-logic façade the server RPCs call. Stateless, no constructor (matches existing logic
modules). Wraps `PersistUserLogicModule` + `PasswordUtil`, enforces rules, returns the §4 DTOs/results.

- `listUsers() -> List[Dict]` — map each `AppUser` → User DTO (roles via `getRoleNamesForUser`).
- `createUser(username, password, displayName, enabled, roleName) -> Dict` — reject blank
  username/password; reject duplicate username (`findUserByUsername`); hash password; save user; assign
  role (reuse the seed flow's user→link pattern). Returns mutation result.
- `updateUser(userId, displayName, enabled, roleName, newPassword|None) -> Dict` — load by id; update
  `displayName`/`enabled`; `replaceUserRoles`; if `newPassword` non-empty, re-hash + set. Username is
  **immutable** (it is the identity / future serial — see §8). Returns mutation result.
- `deleteUser(userId) -> Dict` — guarded delete (§7). Returns mutation result.

> Keeping CRUD in a dedicated `UserAdminLogicModule` (not in `LoginLogicModule`) keeps the read-only
> auth path separate from the privileged write path, and gives #3 a clean place to add the
> profile-binding calls later.

## 6. Server + client RPC layer

### 6.1 `SpectracsPyServer` — add `@expose` methods
Thin pass-throughs to `UserAdminLogicModule` (matches how `login` wraps `LoginLogicModule`):
- `listUsers()`
- `createUser(username, password, displayName, enabled, roleName)`
- `updateUser(userId, displayName, enabled, roleName, newPassword)`
- `deleteUser(userId)`

### 6.2 `SpectracsPyServerClient` — add matching methods
Same shape as `login()`: `getProxy()`; if `None` return `{"ok": False, "message": "server unavailable"}`
(or `[]` for `listUsers`); call `proxy.<method>(...)`; catch all exceptions into an `ok=False` result.
Never raises.

## 7. Safety rules (enforced server-side in `UserAdminLogicModule`)

- **Unique username** on create — reject duplicates with a clear message.
- **Non-empty username** on create; **free-text format** (no charset/space constraint — Roadmap #3
  introduces any serial-format rule when username becomes the serial) *(decision R5)*.
- **Password minimum length: 8 characters** *(decision R4)* — enforced on create and on edit-reset.
  (On edit, a blank password means "unchanged" and skips the length check.)
- **Last-master-user guard:** refuse to delete, disable, or role-demote the *only* remaining enabled
  `MASTER_USER` (`countUsersWithRole` == 1). Prevents locking everyone out of admin.
- **Username immutable** after creation (identity / future serial).
- **Self-edit allowed** *(decision R2)*: a master may change their own role/`enabled` (subject to the
  last-master guard); such changes take effect on next login — the UI shows a notice, the live
  `CurrentUserSession` is not retro-patched.

(The UI mirrors these as inline validation, but the server is the authority — it returns `ok=False` +
`message`, which the dialog surfaces.)

## 8. UI (`spectracsPy`) — follows the `PageWidget` list/edit template

### 8.1 `UserListViewModule(PageWidget)` — a **table** of AppUsers *(decision Q3)*
`view/settings/user/UserListViewModule.py`.
- A **`QTableView`** (NoEditTriggers, `SelectionBehavior.SelectRows`, single-row selection) backed by a
  `UsersTableModel(QAbstractTableModel)` whose rows are User DTOs from
  `SpectracsPyServerClient().listUsers()`. Columns: **Username · Display name · Role · Enabled**.
  (A table, not the `QListView`+`HTMLDelegate` used by `SpectrometerProfileListViewModule` — this
  screen wants a tabular, selectable grid.)
- Rows are **selectable**; the selected row drives **Edit** and **Delete**.
- Nav buttons: **Back, Add, Edit, Delete** (Delete is new — no existing precedent; confirm via a
  `QMessageBox`). Double-clicking a row = Edit.
- Add → emit nav to `UserViewModule`, grab it via `getViewModule(...)`, `loadView(None)` (new user).
- Edit → load selected DTO into `UserViewModule.loadView(dto)`, then navigate.
- Delete → confirm, call `deleteUser(userId)` (**hard delete**, decision Q2), on `ok` re-fetch the
  list; on `!ok` show `message` (e.g. the last-master-user guard).
- Refreshes on a new **`userSignal`** (see §8.3) — re-fetches from the server (the list is
  server-owned, so refresh = re-`listUsers()`, not local mutation).
- **Server-offline banner** *(decision R3)*: if `listUsers()` returns the unavailable sentinel (proxy
  `None`), show an explicit "server unavailable" banner above the table rather than an empty grid that
  reads as "no users." (Editor saves likewise surface `"server unavailable"` from the `ok=False` result.)

### 8.2 `UserViewModule(PageWidget)`
`view/settings/user/UserViewModule.py`. Editor form via `createLabeledComponent(...)`:
- `username` — `QLineEdit`; editable only when creating, **read-only when editing**.
- `displayName` — `QLineEdit`.
- `password` — `QLineEdit` (`EchoMode.Password`); on **create** required (**min 8 chars**, decision R4),
  on **edit** blank = unchanged (label hints "leave blank to keep current"; if non-blank, min 8 applies).
- `role` — `QComboBox` populated from `UserRoleType` values. **Single role** *(decision Q1)* — the
  `replaceUserRoles(List)` API stays multi-capable so multi-role can be added later without a model change.
- `enabled` — `QCheckBox`.
- Holds a `dto`/`getModel`/`setModel`/`loadView(dto|None)` quartet (mirror `SpectrometerProfileViewModule`).
- **Save** → gather fields → `createUser(...)` (new) or `updateUser(...)` (existing) over Pyro → on
  `ok` emit `userSignal` (CREATE/UPDATE) so the list refreshes, then navigate Back; on `!ok` show
  `message` in a `QMessageBox` (no navigation).

### 8.3 New `UserSignal` + bus method
- `UserSignal` analogous to `SpectrometerProfileSignal` (carries the User DTO + a
  `DbEntityCrudOperation`).
- `ApplicationSignalsProviderLogicModule`: add `userSignal = Signal(UserSignal)` + `emitUserSignal(...)`.
  (Distinct from the parameterless `userSessionSignal`, which is about *login state*, not the user list.)

### 8.4 Registration (three hardcoded touch-points — same as every screen)
1. `MainViewModule` — instantiate `UserListViewModule` + `UserViewModule`, `addWidget` at two new
   indices, `.initialize()` them.
2. `NavigationHandlerLogicModule` — add both target strings to **both** `if/elif` chains
   (`handleNavigationSignal` title + `__getWidgetIndex`) with the new indices.
3. `SettingsViewModule` — add an **"Administration"** group box with a **"Users"** button that
   navigates to `UserListViewModule`.

### 8.5 Role gate (this screen is phase-G's first consumer)
- The **"Users" button** (and ideally the whole Administration group) is shown only when
  `CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value)`.
- `SettingsViewModule` connects to `userSessionSignal` and re-evaluates visibility on login/logout.
- Defense in depth: `UserListViewModule.initialize()` also checks the role and renders an empty/"not
  authorized" state if reached without it.

## 9. Known gaps / honest caveats

- **CRUD RPCs are transport-unauthenticated** (like `login` today): a Pyro client could call them
  directly, bypassing the UI role gate. Acceptable for the current loopback/dev posture; real
  enforcement waits on Step-2 session tokens + TLS (phases D & the deferred auth work). Documented, not
  silently assumed.
- Passwords cross the wire in plaintext until TLS (phase D).
- The two seeded dev users remain (`endUser`, `masterUser`) — this screen can now edit/delete them
  (subject to the last-master guard).

## 10. File-change checklist (for the eventual implementation request)

**`spectracsPy-model`**
- `logic/persistence/database/user/PersistUserLogicModule.py` — add `findUserById`, `listAllUsers`,
  `updateUser`, `deleteUser`, `replaceUserRoles`, `countUsersWithRole`.
- `logic/user/UserAdminLogicModule.py` — **new** (list/create/update/delete + rules).

**`spectracsPy-server`**
- `SpectracsPyServer.py` — add four `@expose` user-CRUD methods.

**`spectracsPy`**
- `logic/server/spectracs/SpectracsPyServerClient.py` — add four client methods.
- `model/signal/UserSignal.py` — **new** (or wherever `SpectrometerProfileSignal` lives).
- `controller/application/ApplicationSignalsProviderLogicModule.py` — add `userSignal` +
  `emitUserSignal`.
- `view/settings/user/UserListViewModule.py` — **new**.
- `view/settings/user/UserViewModule.py` — **new**.
- `view/main/MainViewModule.py` — register the two screens.
- `controller/application/navigationHandler/NavigationHandlerLogicModule.py` — route the two targets.
- `view/settings/SettingsViewModule.py` — Administration group + Users button + role-gated visibility.

## 11. Decisions (resolved 2026-06-30)

- **Q1 — Single role per user.** `QComboBox`, one `UserRoleType` value. `replaceUserRoles(List)` stays
  multi-capable for the future.
- **Q2 — Hard delete.** A Delete button performs a real delete (user + role links), behind a confirm
  dialog and the last-master-user guard. (`enabled` remains as an independent active/inactive flag.)
- **Q3 — Dedicated view in Settings → Administration**, presented as a **table of AppUsers**
  (selectable / editable / deletable). See §8.1.

## 12. Rubber-duck decisions (resolved 2026-06-30)

- **R1 — Separate editor page** (no in-cell editing). The table selects; Add/Edit open `UserViewModule`.
- **R2 — Self-edit allowed for now**, with a "takes effect on next login" notice; `CurrentUserSession`
  is not retro-patched. (Still subject to the last-master guard.)
- **R3 — Explicit "server unavailable" banner** when the proxy is unreachable (not an empty table).
- **R4 — Password minimum length 8 characters** (create + edit-reset).
- **R5 — Username stays free-text**; Roadmap #3 introduces any serial-format rule.

## 13. Implementation phases

Bottom-up: each phase compiles and is independently testable before the next. Phases 1–2 are pure
`spectracsPy-model`/`-server` (no UI); the screen only lights up at Phase 4.

| # | Phase | Repo(s) | Deliverable | Files | Verify |
|---|-------|---------|-------------|-------|--------|
| **1** | Persistence primitives | `-model` | `findUserById`, `listAllUsers`, `updateUser`, `deleteUser` (+ links), `replaceUserRoles`, `countUsersWithRole` | `logic/persistence/database/user/PersistUserLogicModule.py` | Unit test against the server DB: create→list→update→delete round-trip; link rows cleaned on delete |
| **2** | Admin façade + rules | `-model` | `UserAdminLogicModule` (`listUsers`/`createUser`/`updateUser`/`deleteUser`) returning §4 DTOs; bcrypt hashing; min-8 password; unique/immutable username; last-master guard | `logic/user/UserAdminLogicModule.py` (new) | Unit tests for each rule (duplicate username, short password, delete-last-master rejected, hash never in output) |
| **3** | RPC wiring | `-server` + `spectracsPy` | 4 `@expose` methods + 4 client methods (never-raise, `ok=false` on failure / unavailable sentinel) | `SpectracsPyServer.py`; `logic/server/spectracs/SpectracsPyServerClient.py` | Run server; from a client REPL call each RPC end-to-end; kill server → confirm graceful `ok=false`/`[]` |
| **4** | List screen (table) | `spectracsPy` | `UserListViewModule` (QTableView + `UsersTableModel`); Back/Add/Edit/Delete; delete confirm; offline banner; registration in `MainViewModule` + `NavigationHandlerLogicModule` | `view/settings/user/UserListViewModule.py` (new) + the 2 registration files | Launch app, navigate Settings→Users, see seeded users in the grid; delete with confirm |
| **5** | Editor screen + refresh signal | `spectracsPy` | `UserViewModule` (form, create/update over Pyro, validation); `UserSignal` + `emitUserSignal`; list refreshes on save | `view/settings/user/UserViewModule.py` (new); `model/signal/UserSignal.py` (new); `ApplicationSignalsProviderLogicModule.py` | Add a user → appears in table; edit (blank password keeps it) → row updates; self-edit notice shows |
| **6** | Role gate + polish | `spectracsPy` | Administration group + Users button in `SettingsViewModule`, gated on `hasRole(MASTER_USER)` + `userSessionSignal`; defense-in-depth check in `UserListViewModule.initialize()` | `view/settings/SettingsViewModule.py` | Logged out / as END_USER → no Users entry; as MASTER_USER → visible; toggles live on login/logout |

**Suggested commits:** one per phase (Phases 1–2 may pair). Phase 3 is the integration seam — verify
the full RPC round-trip there before touching any UI. Phases 4–6 are the only ones that change visible
behaviour.

> **Definition of done for #4:** as `masterUser`, you can open Settings → Users, see the table, add /
> edit / delete a user with validation and the last-master guard working, and the entry is invisible to
> non-masters — all over Pyro against the server-owned user DB.
