# Spec — Users, roles & server-side login (master / end-user gate)

Status: **Step 2a IMPLEMENTED 2026-06-28** (login/logout via the Settings button, two seeded dev users).
**TLS (§6, phase D) and the role gate (§8, phase G) are NOT yet built.** Spec-first; build on explicit request only.

> **Implementation notes (2026-06-28, Step 2a = phases A–C, E, F).** Built the auth backbone + button,
> login/logout over **plaintext loopback** (TLS deferred to the immediate next step 2b, per the agreed
> sequencing). Verified headless: seed is idempotent (double-seed → 2 users); `login()` returns roles for
> `masterUser/masterUser` (`MASTER_USER`) and `endUser/endUser` (`END_USER`), rejects bad creds with a
> generic message, and **never** carries `passwordHash`. Verified the full **Pyro round-trip** against a
> live local server, plus graceful degrade to `"server unavailable"` when no server is up. Decisions taken
> (my leans, unopposed): modal `ServiceLoginDialog`; button toggles `Login` ↔ `Logout (<username>)`;
> `login()` returns a **plain dict** over the wire (no serializer registration); the two users are
> **dev-only** plaintext creds. `bcrypt` 5.0.0 installed into the shared app/server venv. New separate DB
> confirmed at `~/.spectracs/spectracsPyServer.db` holding **only** the three user tables. Files: see §3
> (all created as specced; `LoginLogicModule`/`UserSeedLogicModule` added under `logic/user/`,
> `UserRoleType` under the entity package). **Still pending:** D (TLS) next, then G (role-gate show/hide).
Scope: a `User` / role data model + a **server-authenticated login** over the existing Pyro5 channel,
to power the two-audience **role gate** (master ↔ end-user) described in
`spectracs-docs/SPECTRAL_WORKFLOW_CONCEPT.md` §7. This is **Step 2** of the locked build sequence
(Step 1 = color-utility extraction); building it first is acceptable.

> **Why server-side.** The user store is **server-owned**. The client never queries the user tables; it
> calls one RPC (`login`) and receives a DTO with the user's roles — **never the password hash**. This
> ties into the longer-term vision (concept doc §7–8): the **serial becomes the username**, and login
> eventually downloads the caller's SpectrometerProfile + Plugin Module.

---

## 1. Decisions locked (this spec)

| # | Decision | Rationale |
|---|---|---|
| 1 | Term is **role**, not "rule" (`UserRole`, not `UserRule`) | `END_USER`/`MASTER_USER` are roles; matches the concept doc's "role gate". |
| 2 | Entity/table prefix **`AppUser…`** (`app_user`, `app_user_role`, `app_user_to_app_user_role`) | `user` is a reserved word in Postgres/MySQL; harmless in SQLite today but cheap insurance. Prefix applied consistently across all three entities (per Edwin). |
| 3 | **Normalized RBAC** — a `AppUserRole` table + a join, not an enum column | Edwin asked for three entities; correct RBAC shape; lets roles grow. Paired with a code-side `UserRoleType` enum + idempotent seeding. |
| 4 | **Many-to-many** user↔role (composite-PK join) | A master can also be an end user; future-proof. Mirrors the existing `ApplicationConfigToSpectrometerProfile` join. |
| 5 | **Server owns the user store in its own DB** (separate SQLite file) | Edwin: "in the server's DB … should be two separate local DBs anyway." Requires a 2nd engine/base — see §4. |
| 6 | **Passwords hashed with `bcrypt`**, server-side only | Modern, salted (PHC string embeds salt+cost). Never sha256/md5. |
| 7 | **TLS on the Pyro channel now** (Pyro5 SSL), not deferred | Edwin: "handle this sec issue already now." Login sends a plaintext password; the wire must be encrypted. See §6. |
| 8 | **Seed roles + a bootstrap master user** at server startup | Otherwise login is a locked door with no key. |
| 9 | **No session token yet** — login returns roles; app holds "current user" in memory | A real session/token comes when RPCs need per-call auth (e.g. "download my profile"). Deferred. |

---

## 2. Object model (ASCII)

```
   ┌────────────────────────┐        ┌─────────────────────────────────┐        ┌────────────────────────┐
   │ AppUser                │        │ AppUserToAppUserRole (join)     │        │ AppUserRole            │
   │  table: app_user       │ 1    n │  table: app_user_to_app_user_…  │ n    1 │  table: app_user_role  │
   ├────────────────────────┤◄───────┤─────────────────────────────────├───────►├────────────────────────┤
   │ id           PK uuid   │        │ app_user_id       PK FK→app_user│        │ id     PK uuid         │
   │ username     unique    │        │ app_user_role_id  PK FK→app_user_role│   │ name   unique          │ ← seeded:
   │ passwordHash           │        └─────────────────────────────────┘        │                        │   END_USER
   │ displayName  (opt)     │                                                    └────────────────────────┘   MASTER_USER
   │ enabled      Bool=True │           (composite PK = both FKs, exactly the
   └────────────────────────┘            ApplicationConfigToSpectrometerProfile shape)
```

### 2.1 `AppUser`

| field | type | notes |
|---|---|---|
| `id` | `String` PK uuid | inherited from `DbBaseEntityMixin` |
| `username` | `String`, unique | **eventually = the serial number** |
| `passwordHash` | `String` | bcrypt PHC string — **server-side only, never serialized to the client** |
| `displayName` | `String`, nullable | optional friendly name |
| `enabled` | `Boolean`, default `True` | disable an account without deleting it |
| `userRoles` | `relationship` via join | the user's roles |

### 2.2 `AppUserRole`

| field | type | notes |
|---|---|---|
| `id` | `String` PK uuid | inherited |
| `name` | `String`, unique | one of `UserRoleType` (`END_USER`, `MASTER_USER`) |

Seeded idempotently (find-or-create by `name`) at server startup from the code enum.

### 2.3 `AppUserToAppUserRole` (join — composite PK)

Copies `ApplicationConfigToSpectrometerProfile` verbatim in shape:

```python
class AppUserToAppUserRole(ServerDbBaseEntity, DbBaseEntityMixin):
    app_user_id:      Mapped[str] = Column(ForeignKey("app_user.id"),      primary_key=True)
    app_user_role_id: Mapped[str] = Column(ForeignKey("app_user_role.id"), primary_key=True)
    appUserRole:      Mapped["AppUserRole"] = relationship("AppUserRole")
```

> Naming note: the codebase's join convention is `…To…` (`ApplicationConfigToSpectrometerProfile`),
> so this spec uses `AppUserToAppUserRole` rather than the `User2UserRole` shorthand from the request.

### 2.4 Code-side enum (not persisted)

```python
class UserRoleType(Enum):
    END_USER    = "END_USER"
    MASTER_USER = "MASTER_USER"
```

Code references the enum; the DB stores rows seeded from it. Single source of truth for the names.

---

## 3. File layout (new files)

**`spectracsPy-model`** (shared model repo) — entity classes + the server engine/base:

```
sciens/spectracs/model/databaseEntity/
  DbServerBase.py                         (NEW) 2nd engine + ServerDbBaseEntity base + server_session_factory()  — §4
  application/user/
    AppUser.py                            (NEW)
    AppUserRole.py                        (NEW)
    AppUserToAppUserRole.py               (NEW)
sciens/spectracs/model/util/
    UserRoleType.py                       (NEW) the enum
sciens/spectracs/logic/persistence/database/user/
    PersistUserLogicModule.py             (NEW) lookup-by-username, save, seed       — server-side CRUD
    PasswordUtil.py                       (NEW) bcrypt hash() / verify()
    UserSeedLogicModule.py                (NEW) seed roles + bootstrap master
```

**`spectracsPy-server`**:

```
sciens/spectracs/SpectracsPyServer.py     (EDIT) add @expose login(); call seed at startup; enable SSL (§6)
sciens/spectracs/auth/LoginResult.py      (NEW) plain serializable DTO (no hash)     — §5
```

**`spectracsPy`** (client/app):

```
sciens/spectracs/logic/server/spectracs/SpectracsPyServerClient.py   (EDIT) add login(); SSL client config
sciens/spectracs/logic/session/CurrentUserSession.py                 (NEW) in-memory current user + roles (Singleton)
sciens/spectracs/view/settings/SettingsViewModule.py                 (EDIT) wire the dead "Service Login" button → login dialog
```

> Exact homes are a starting point; adjust to match conventions found during build.

---

## 4. Two separate databases (the wrinkle)

**Current reality:** `SpectracsPyServer.py` imports `session_factory` + `app_paths` from the *shared*
`DbBase.py`, which hardcodes `sqlite:///<appdata>/spectracsPy.db`. **The app and server open the exact
same file today** — there is no separation.

**Required:** the user store lives in a **separate server DB**. Implement a parallel engine/base, leaving
the existing app DB untouched:

```python
# DbServerBase.py  (NEW, in spectracsPy-model)
serverDbFilepath  = 'sqlite:///' + app_paths.app_data_path + '/spectracsPyServer.db'
serverEngine      = create_engine(serverDbFilepath)
ServerDbBaseEntity = declarative_base()          # SEPARATE metadata from DbBaseEntity
_ServerSessionFactory = sessionmaker(bind=serverEngine, expire_on_commit=False)

def server_session_factory() -> Session:
    ServerDbBaseEntity.metadata.create_all(serverEngine)   # only the user tables
    return _ServerSessionFactory()
```

- The three user entities extend **`ServerDbBaseEntity`** (not the app's `DbBaseEntity`). Because the two
  declarative bases have **separate `metadata`**, `create_all` on each side only builds *its own* tables:
  the user tables exist **only** in `spectracsPyServer.db`; the app's `create_all` never sees them.
- `DbBaseEntityMixin` is just a mixin (uuid `id`, snake_case `__tablename__`, serializer) — reused as-is by
  both bases.
- The server keeps using the existing shared `session_factory()` for the master data it already publishes
  (spectrometers, spectral-line master data); the **user store uses `server_session_factory()`**. (Folding
  the published master-data store into the server DB too is a larger refactor, **out of scope here.**)

---

## 5. Login over Pyro — flow & contract

The password hash **never leaves the server**. Login is one RPC returning a hash-free DTO.

```
client (app)                              server (SpectracsPyServer, @expose)
────────────                              ───────────────────────────────────
SpectracsPyServerClient.login(u, p) ─RPC─► login(username, password):
                                              user = PersistUserLogicModule.findByUsername(username)
                                              if user and user.enabled and
                                                 PasswordUtil.verify(password, user.passwordHash):
                                                  roles = [r.name for r in user roles]
                                                  return LoginResult(ok=True, userId=user.id,
                                                                     username=user.username, roles=roles)
                                              return LoginResult(ok=False, message="invalid credentials")
  ◄──────────────── LoginResult ──────────────┘
CurrentUserSession.set(result)  →  role gate flips (master shows authoring; end-user shows run-workflow)
```

**`LoginResult`** is a **plain serializable class** (or dataclass) — deliberately **not** a SQLAlchemy
entity:

```python
class LoginResult:
    ok: bool
    userId: str | None
    username: str | None
    roles: list[str]            # e.g. ["MASTER_USER"]
    message: str | None         # populated on failure
```

- Register it with the Pyro5 serializer (`register_class_to_dict` / `register_dict_to_class`), mirroring
  `SqlAlchemySerializer`; or return a plain `dict` (zero ceremony). **Recommended: the small class** for
  clarity at the call site.
- Returning a DTO (not `AppUser`) both sidesteps the per-entity serializer ceremony **and** structurally
  guarantees `passwordHash` can't leak.
- **Don't leak account existence:** same generic `"invalid credentials"` for unknown-user and wrong-password.
- **Never log the password** (or the hash) — scrub from any RPC tracing.

---

## 6. TLS on the Pyro channel (handle now)

Login transmits a plaintext password; **the channel must be encrypted now**, not when the server goes
remote. Pyro5 has built-in SSL.

- **Enable SSL globally** (it covers the nameserver, the daemon, *and* the existing RPCs like
  `getSpectrometers` — a global `Pyro5.config` setting, not per-method):
  - Server: `Pyro5.config.SSL = True`, `SSL_SERVERCERT = <cert.pem>`, `SSL_SERVERKEY = <key.pem>`.
  - Client: `Pyro5.config.SSL = True`, `SSL_CACERTS = <cert.pem>` to trust the server's cert.
- **Local dev:** generate a self-signed server cert/key once
  (`openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 3650 -nodes`); the client
  trusts that cert via `SSL_CACERTS`. Keep `key.pem` out of git.
- **Mutual TLS (optional, later):** `SSL_REQUIRECLIENTCERT = True` + client cert — defer; one-way TLS
  (encryption + server authentication) is the needed baseline.
- **Note:** even under TLS the server necessarily sees the plaintext password to verify it — that is normal
  and correct. TLS protects against on-wire eavesdropping; bcrypt protects the at-rest store. (A
  challenge-response/SRP scheme so the password is never transmitted at all is a *later* hardening, not
  required now. Client-side pre-hashing is **not** a substitute — the pre-hash just becomes the password.)

---

## 7. Seeding & bootstrap (so login isn't a locked door)

At server startup (idempotent, safe to run every boot):

1. **Roles:** for each `UserRoleType`, find-or-create an `AppUserRole` row by `name`.
2. **Bootstrap master:** if no `MASTER_USER` exists, create one default master account with
   username + password from **config** (env var / config file — not hardcoded in source). On first run the
   password should be forced-changed or clearly flagged as a dev default.

> A real "create user" / "publish serial" admin flow is future work; the bootstrap master is just enough to
> log in and exercise the role gate.

---

## 8. Client-side role gate (consumes login)

- `CurrentUserSession` (Singleton) holds the `LoginResult` after a successful login: `userId`, `username`,
  `roles`. Default = logged-out (no roles).
- The dead **"Service Login"** button (`SettingsViewModule.py:80–91`) gets a handler → a small
  username/password dialog → `SpectracsPyServerClient.login()` → store in `CurrentUserSession` → emit a
  signal so views re-evaluate visibility.
- **Role gate = show/hide on the same screens** (concept doc §7), *not* a separate UI:
  - `MASTER_USER` → sees authoring/settings/calibration/publish.
  - `END_USER` → sees only the run-workflow screen (+ optionally a read-only SpectrometerProfile).
- Building the *actual* per-widget show/hide wiring is the back half of Step 2; this spec lays the data +
  login plumbing it depends on.

---

## 9. Build phases

| Phase | Status | Deliverable | Verify |
|---|---|---|---|
| A | ✅ done | `DbServerBase.py` (2nd engine/base/session) + the three entities + `UserRoleType` | server DB file created; user tables in `spectracsPyServer.db` only, **not** in `spectracsPy.db` |
| B | ✅ done | `PasswordUtil` (bcrypt) + `PersistUserLogicModule` (findByUsername/save) | hash/verify round-trips; lookup works |
| C | ✅ done | `UserSeedLogicModule` + call at server startup | roles seeded once; dev users created; idempotent on reboot |
| D | ⏳ next (2b) | TLS: self-signed cert, server + client SSL config | existing RPCs (`getSpectrometers`) still work **over SSL**; plaintext connection refused |
| E | ✅ done | `@expose login()` returning a plain dict (no serializer registration needed — see note) | RPC returns roles on valid creds, generic failure otherwise; **no `passwordHash` in the payload** |
| F | ✅ done | Client `login()` + `CurrentUserSession` + wire the "Service Login" button | end-to-end login from the app flips current-user state |
| G | ⬜ pending | Role-gate show/hide across views | master vs end-user see the right screens |

Phases A–F are the auth backbone; G is the visible payoff. A–C are server-only and testable headless.

> **Decision delta vs §5:** the `login()` RPC returns a **plain dict** `{ok,userId,username,roles,message}`
> rather than a registered `LoginResult` class — Pyro's serpent serializer handles dicts natively, so this
> dropped the per-class serializer registration with no loss (the no-hash guarantee still holds: the dict is
> built by hand from safe fields). `CurrentUserSession` consumes the dict directly.

### 9a. Definition of Done — Step 2a (login/logout via the Settings button) ✅

**Goal:** from the Settings "Login" button, authenticate against the server and log out again; two seeded
dev users. **Met 2026-06-28.** Acceptance criteria, all verified:

- [x] Three entities (`AppUser`/`AppUserRole`/`AppUserToAppUserRole`) live in a **separate** server DB
      (`~/.spectracs/spectracsPyServer.db`) that holds **only** those three tables — the app DB is untouched.
- [x] `bcrypt` hashing; seeding is **idempotent** (double-seed → still exactly 2 users).
- [x] Two dev users seeded at server startup: `masterUser/masterUser` → `MASTER_USER`,
      `endUser/endUser` → `END_USER` (plaintext **dev-only** creds — must not ship).
- [x] `@expose login()` over Pyro returns the user's roles on valid creds; generic `"invalid credentials"`
      on bad creds or unknown user; **`passwordHash` never appears in the payload** (asserted in test).
- [x] Verified over a **live Pyro round-trip** (not just the logic) for both users + a bad-cred case.
- [x] Client `login()` degrades gracefully to `"server unavailable"` when no server is running (no crash).
- [x] The Settings button toggles **Login ↔ Logout (\<username\>)**; logout drops the in-memory session
      (`CurrentUserSession`). Modal `ServiceLoginDialog` collects creds, shows an inline error on failure.
- [x] All touched files `py_compile`-clean; app + server import chains clean.

**Explicitly NOT in this DoD (next steps):** TLS (phase D / Step 2b — login is currently plaintext over
loopback) and the role-gate show/hide (phase G — `endUser` vs `masterUser` see no UI difference yet).

---

## 10. Dependencies

- **`bcrypt`** (new) — password hashing. Single small wheel. (Alternative: `argon2-cffi`.)
- **Pyro5 SSL** — no new package; uses Python's stdlib `ssl` + a generated cert.

---

## 11. Out of scope (explicitly deferred)

- Session tokens / per-RPC authentication (decision #9).
- Mutual TLS / client certificates.
- A full user-admin / serial-publishing UI (only a bootstrap master here).
- Folding the published master-data store into the server DB.
- Password-reset, lockout/rate-limiting, account self-registration.
- The download-profile-and-plugin-on-login behavior (concept doc §8) — depends on the plugin system.

---

## 12. Maintenance

⚠️ Per the standing rule: **if these entities or the login contract change once implemented, update
`spectracs-docs/DB_ENTITIES.md` (+ `db_entities.puml`/`.svg`) and `SPECTRAL_WORKFLOW_CONCEPT.md` §7** to
match. This SPEC is the design of record until then.
