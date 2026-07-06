# SPEC — PayPal payment (SaaS billing · milestone 1: single sandbox payment)

> Status: **MILESTONE 1 DONE — P1 + P2 + P3 IMPLEMENTED + CLICK-THROUGH VERIFIED 2026-07-06.** The full
> flow works end-to-end in the running desktop app: account menu → Account settings → Payment → Pay 1,00 €
> → approve in browser as the sandbox buyer → capture → `CAPTURED` transaction listed (Edwin confirmed).
> Backend also live-verified via `verify_paypal_payment.py` (token/createOrder/capture) and offscreen
> tests (entity CRUD, screen build, formatters, refresh). As-built in **§11** (backend) + **§12** (UI).
> Later milestones: M2 recurring €200 subscription, M3 live go-live, M4 Android.
>
> Original status: **DESIGN ONLY — not implemented.** This spec covers the *first
> sub-milestone*: a single, one-off €1 payment from a logged-in `AppUser` to a **dev PayPal
> recipient**, executed against the **PayPal sandbox**, recorded as a server-side `Transaction`,
> and listed on a new per-user **Account settings** screen (Payment tab). The recurring monthly
> **rental fee** (you pay even without using the software) is the *product* model but is **out of
> scope here** — it is a different PayPal API (Subscriptions) and will get its own spec once the
> one-off flow is factually sound (Edwin, 2026-07-06). Realises a new Roadmap item ("SaaS payment").
> Implement only on explicit request (spec-first workflow).
>
> Related: `SPEC_user_auth_login.md`, `SPEC_user_crud.md`, `SPEC_login_header_placement.md`,
> `SPEC_connection_and_calibration_ux.md`.

## 1. Purpose & scope

Add **payment** to the Spectracs SaaS. The product is a **monthly rental** — an end user pays a
recurring fee regardless of usage. We build it in factual, verifiable slices; recurring billing is
only sound once we can create, approve, capture and record a *single* real payment. So:

**In scope (milestone 1):**
- A new server-side **`Transaction`** entity (server DB, alongside `AppUser`).
- A **PayPal Orders v2** one-off payment flow, **sandbox** only, fixed **€1** amount, payee = a
  fixed **dev recipient** (sandbox business account).
- A new **Account settings** screen reachable from the **account button menu** in the header, with a
  **Payment** tab: a "Pay €1 (sandbox)" action + a table of *this user's* transactions.
- Server RPCs (`createPayment` / `capturePayment` / `listTransactions`) + client proxy mirrors.

**Out of scope (later milestones / own specs):**
- Recurring **monthly €200 subscription** (PayPal Subscriptions API — P-future).
- **Live** (production) PayPal credentials & go-live (P-future).
- **Android** payment path (redirect/return handling differs; the header menu is skipped on Android
  anyway — see §4.3). Milestone 1 is **desktop-only**.
- Invoicing / VAT / receipts / refunds / dunning.

## 2. Current state (as found)

Grounded in the four `sciens/` trees under `spectracsPy`, `spectracsPy-model`, `spectracsPy-server`,
`spectracsPy-base`. (`android/`, `.buildozer/`, `venv/` are build artifacts — ignored.)

### 2.1 Users & the server DB
`spectracsPy-model/sciens/spectracs/model/databaseEntity/application/user/AppUser.py` —
`AppUser(ServerDbBaseEntity, DbBaseEntityMixin)` with `username, passwordHash, displayName, enabled,
email, firstName, lastName, registeredSerial`.

- `DbBaseEntityMixin` (`.../databaseEntity/DbBase.py`) supplies PK `id = Column(String,
  primary_key=True, default=uuid4)`, derives `__tablename__` camel→snake (`AppUser` → `app_user`),
  mixes in `sqlalchemy_serializer.SerializerMixin`, `__table_args__ = {'extend_existing': True}`.
- `ServerDbBaseEntity` (`.../databaseEntity/DbServerBase.py`) is a **separate declarative_base with
  its own metadata and its own SQLite file** `spectracsPyServer.db` — distinct from the app's
  `spectracsPy.db`. Sessions via `server_session_factory()` / `ServerSessionProvider` (Singleton).
- Roles are a link table: `AppUserRole` / `AppUserToAppUserRole`; `UserRoleType { END_USER,
  MASTER_USER }`. `AppUser` has no direct role `relationship`.

**No `Transaction`, `Payment`, `Order`, `Invoice`, or `Subscription` entity exists anywhere in clean
source.** A payment record is a brand-new entity and belongs on the **server DB** (money must be
server-authoritative; never in the on-device `spectracsPy.db`).

### 2.2 Server RPC layer (Pyro5)
- **Server:** `spectracsPy-server/sciens/spectracs/SpectracsPyServer.py` — each RPC is a thin
  `@expose`d method delegating to a logic module, e.g.
  ```python
  @expose
  def login(self, username, password) -> Dict:
      return LoginLogicModule().login(username, password)
  @expose
  def createUser(self, username, password, displayName, enabled, roleName) -> Dict:
      return UserAdminLogicModule().createUser(...)
  ```
  Logic modules live in `spectracsPy-model/.../logic/user/` (`LoginLogicModule`,
  `UserAdminLogicModule`, `RegisterUserLogicModule`, `PasswordUtil`, …). **DTOs crossing the wire are
  always plain dicts** — never entities, never the password hash.
- **Client proxy:** `spectracsPy/sciens/spectracs/logic/server/spectracs/SpectracsPyServerClient.py`
  — `getProxy()` resolves local URI → dev nameserver → remote `DAEMON_NAT_HOST` (sciens.at),
  `COMMTIMEOUT=5.0`. Every method is defensive: get proxy; if `None` return a
  `{"ok": False, ..., "message": "server unavailable"}` dict; else `try proxy.X(...) except` →
  failure dict. Existing: `login, listUsers, createUser, updateUser, deleteUser, setRegisteredSerial,
  resolveInstrumentBySerial, registerEndUser, listPlugins, savePlugin, save/listSpectrometer*,
  syncSpectrometers, syncSpectralLineMasterDatas`.
- Server bootstrap: `spectracsPy-server/service_pyro.py`, `main.py`, `spectracsPyServer.py`.

### 2.3 The account button + its menu (UI entry point)
`spectracsPy/sciens/spectracs/view/main/MainStatusBarViewModule.py` — `self.accountButton`
(`QToolButton`, person icon) in the header (per `SPEC_login_header_placement.md`).

- `onClickedAccountButton()` (~line 254): **logged in on desktop** builds a `QMenu` — disabled
  header action `"username (roles)"`, separator, `"Logout"` — shown via `menu.exec(...)` positioned
  under the button. **On Android it skips the QMenu** (Qt-for-Android single-window popup crash) and
  logs out directly. Logged-out → navigates to in-window `LoginViewModule`.
- Ctrl+L bound app-wide to the same handler (~line 79).
- `updateAccountControl()` (~line 188) swaps icon grey↔green + tooltip on `userSessionSignal`.

**This QMenu is the extension point** for a new "Account settings…" action. ⚠️ Android skips the
menu entirely → the account screen is desktop-only for milestone 1 (consistent with §1 out-of-scope).

### 2.4 Settings vs. a per-user account screen
`spectracsPy/sciens/spectracs/view/settings/SettingsViewModule.py` — `SettingsViewModule(QWidget)`,
a **single-column `QGridLayout` of `QGroupBox` sections** (Acquisition, Downloads, Infos,
master-only Administration, Development, nav). **Not tabbed.** This is *app/admin config*, not
per-user account data — the payment screen must **not** live here.

`QTabWidget` is the established idiom elsewhere (`view/playground/PlaygroundViewModule.py`,
`SpectrometerCalibrationProfileViewModule.py`, `WizardViewModule.py`) via `addTab(widget, "Label")`.

Navigation is signal-based: `NavigationSignal` → `NavigationHandler`, string targets like
`"UserListViewModule"`. A new screen registers a new target string.

## 3. Design decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Where the payment record lives | **New `Transaction` entity on the server DB** (`ServerDbBaseEntity`), FK to `app_user`. Never on the app DB. Server is the authority for money. |
| D2 | PayPal API for milestone 1 | **Orders v2 (Checkout)** — create order → user approves in browser → capture. One-off, correct primitive. Subscriptions API deferred to the recurring milestone. |
| D3 | Environment | **Sandbox only.** A single `PAYPAL_ENV` switch (`sandbox`/`live`) selects base URL + credential set; live is a later milestone. |
| D4 | Credential storage | **Client id + secret live on the SERVER only**, in a `.env` under the **external, un-versioned config folder** `/home/nidwe72/development/spectracs/spectracsPy-server-config/.env` (outside all four repos — the server has no config mechanism today, OQ3). Loaded at server startup. Never in any repo, APK, DB, or over the wire to the client. A blank **`.env.example`** committed in `spectracsPy-server` documents the keys. **(Security-critical.)** Server code locates the dir via `SPECTRACS_SERVER_CONFIG_DIR`, defaulting to this path (folder renamed 2026-07-06, typo fixed). |
| D5 | Who approves | The **end user** (payer) approves in **their own** PayPal login, in the **system browser**. We never see/store their PayPal credentials. Payee is the fixed dev **sandbox business** account. |
| D6 | Approval → capture handshake (desktop) | Client opens the PayPal **approval URL** in the system browser (`QDesktopServices.openUrl`), shows a modal "Waiting for approval…" with a **[I've approved / check status]** button; on click the client calls server `capturePayment(orderId)`, which reads the order and **captures if APPROVED**. **Polling, not a redirect listener** — no localhost callback server, works without a public return URL. (Alt considered: loopback HTTP listener catching PayPal's `return_url` redirect — more automatic but heavier; deferred.) |
| D7 | Amount / currency (milestone 1) | **Fixed €1.00 EUR**, computed server-side (client cannot set the amount — prevents tampering). Stored as **integer minor units** (`amountMinor = 100`) + `currency = "EUR"`. **Displayed de_AT** → `1,00 €` (comma decimal, trailing symbol); storage stays integer minor units (OQ4). |
| D8 | Account screen | **New shared `AppUserSettingsViewModule(QTabWidget)`** showing the *current* user's own account. Tabs: **Profile** (read-only identity) + **Payment**. One screen for both roles (a master reuses it); the Payment tab is written from the end-user's perspective. Reached from the account-button menu (D9). |
| D9 | Menu entry | Add **"Account settings…"** action to the logged-in `QMenu` in `MainStatusBarViewModule` (above Logout), navigating to the new screen. **Desktop only** — Android skips the QMenu (§2.3). |
| D10 | HTTP client (server side) | Use a plain REST call (`requests`/`httpx` — whichever the server already vendors; else `requests`) inside a `PayPalGateway` wrapper. No heavyweight PayPal SDK; the two endpoints we need are small. Decide the exact lib at impl time from server deps. |

## 4. Target design

### 4.1 `Transaction` entity (server DB)
`spectracsPy-model/.../databaseEntity/application/payment/Transaction.py`

```python
class Transaction(ServerDbBaseEntity, DbBaseEntityMixin):
    # id (uuid PK) + __tablename__ 'transaction' come from DbBaseEntityMixin
    appUserId       = Column(String, ForeignKey("app_user.id"))
    provider        = Column(String, default="PAYPAL")   # future-proof for other gateways
    providerOrderId = Column(String)                     # PayPal order id (create)
    providerCaptureId = Column(String)                   # PayPal capture id (capture), nullable
    amountMinor     = Column(Integer)                    # 100 = €1.00  (integer minor units, D7)
    currency        = Column(String, default="EUR")
    status          = Column(String)                     # see TransactionStatusType
    description     = Column(String)                     # e.g. "Spectracs sandbox test payment"
    createdAt       = Column(DateTime)                   # set server-side at create
    updatedAt       = Column(DateTime)                   # set server-side at capture/fail
```

`TransactionStatusType` (Enum, sibling file): `CREATED, APPROVED, CAPTURED, FAILED, CANCELLED`.

- `'transaction'` is a fine table name; if SQLite/SQLAlchemy quoting complains (reserved-ish word),
  fall back to a `__tablename__` override `"app_transaction"` — decide at impl.
- Money as **integer minor units** avoids float rounding (mirrors the workflow-persistence float-key
  lesson). Never store amounts as float.
- New package `application/payment/` with an `__init__.py`; entity must be **imported at server DB
  init** so `create_all()` builds the table (check how `AppUser` et al. get registered in
  `DbServerBase`/server bootstrap and register `Transaction` the same way).

### 4.2 Server logic + gateway
- **`PayPalGateway`** (server-side, `spectracsPy-server/.../logic/payment/PayPalGateway.py` or model
  logic — place beside where credentials load): reads `PAYPAL_ENV`, `PAYPAL_CLIENT_ID`,
  `PAYPAL_CLIENT_SECRET` from server config/env (D4). Methods:
  - `getAccessToken()` — OAuth2 `client_credentials` against `.../v1/oauth2/token`.
  - `createOrder(amountMinor, currency, description, payeeEmailOrMerchantId)` → returns
    `(orderId, approvalUrl)` from `POST /v2/checkout/orders` (intent CAPTURE, purchase_unit amount,
    payee = dev recipient). `approvalUrl` = the `rel:"approve"` HATEOAS link.
  - `getOrder(orderId)` / `captureOrder(orderId)` → `POST /v2/checkout/orders/{id}/capture`.
- **`PaymentLogicModule`** (`spectracsPy-model/.../logic/payment/`):
  - `createPayment(userId)` — validates the user exists/enabled; **server sets amount = €1** (D7);
    calls `gateway.createOrder`; writes a `Transaction(status=CREATED)`; returns
    `{"ok": True, "orderId", "approvalUrl", "transactionId", "amountMinor", "currency"}` (no secret).
    The client renders the amount from **this response**, never a hardcoded label (RD2).
  - `capturePayment(userId, orderId)` — loads the `Transaction` (must belong to `userId`); calls
    `gateway.captureOrder`; updates status → `CAPTURED` (+ `providerCaptureId`) or `FAILED`/
    `CANCELLED`; returns `{"ok", "status", "message"}`.
  - `listTransactions(userId)` — returns `[dict,...]` of the user's transactions, newest first
    (plain dicts, D2/§2.2 convention).
- **`SpectracsPyServer`** gains three `@expose`d thin delegators mirroring the above.

### 4.3 Client + UI
- **`SpectracsPyServerClient`** gains `createPayment(userId)`, `capturePayment(userId, orderId)`,
  `listTransactions(userId)` — same defensive shape (proxy-None → `{"ok": False, "message": "server
  unavailable"}` / `[]`).
- **`MainStatusBarViewModule.onClickedAccountButton()`**: in the logged-in **desktop** branch, add an
  `"Account settings…"` `QAction` above the separator/Logout, emitting a `NavigationSignal` to
  `"AppUserSettingsViewModule"`. **Android branch unchanged** (still logs out; no menu → no account
  screen this milestone).
- **`AppUserSettingsViewModule(QTabWidget)`** (`view/settings/user/AppUserSettingsViewModule.py` or a
  new `view/account/`):
  - **Profile tab** — read-only labels for the current user (`CurrentUserSession()`): username,
    display name, email, roles. (Editing is existing user-admin scope; not here.)
  - **Payment tab** —
    - a **"Pay 1,00 € (sandbox)"** `QPushButton` (de_AT display, OQ4);
    - on click → `client.createPayment(userId)` → open `approvalUrl` via
      `QDesktopServices.openUrl` (`from PySide6.QtGui import QDesktopServices`) → modal "Waiting for
      approval… [I've approved]"; on confirm → `client.capturePayment(userId, orderId)`. **The Pay/
      confirm buttons disable during the round-trip** (RD4, no double-capture). If capture comes back
      **not** `CAPTURED` (user clicked before actually approving) the modal **stays open** with
      "not approved yet — approve in the browser, then retry" (RD3);
    - a **Transactions `QTableWidget`** (date · amount · currency · status · PayPal order id),
      populated from `client.listTransactions(userId)`, refreshed after a capture and via a manual
      **↻ refresh**.
- **Navigation:** register `"AppUserSettingsViewModule"` in `NavigationHandler` (follow how
  `"UserListViewModule"` is wired).

### 4.5 Screen layouts (ASCII)

**Account-button menu (logged in, desktop) — new entry:**
```
   header right … [ 🟢👤 ]
                  ┌────────────────────────┐
                  │ edwin (master)         │   ← disabled header (existing)
                  ├────────────────────────┤
                  │ Account settings…      │   ← NEW → nav "AppUserSettingsViewModule"
                  │ Logout                 │   ← existing
                  └────────────────────────┘
```

**`AppUserSettingsViewModule` — Payment tab:**
```
┌─ Account settings ──────────────────────────────────────────────────┐
│ ╭ Profile ╮╭ Payment ╮                                               │
│ ┘         └──────────┴───────────────────────────────────────────── │
│                                                                      │
│   Billing — Spectracs SaaS  (sandbox)                                │
│   Plan: monthly rental (M2)          Subscription: — none yet        │
│                                                                      │
│      ┌───────────────────────────────┐                               │
│      │   Pay 1,00 €   (sandbox test) │  → opens PayPal in browser     │
│      └───────────────────────────────┘                               │
│                                                                      │
│   Transactions                                              [ ↻ ]    │
│   ┌────────────┬────────┬──────┬───────────┬────────────────────┐    │
│   │ Date       │ Amount │ Curr │ Status    │ PayPal order id    │    │
│   ├────────────┼────────┼──────┼───────────┼────────────────────┤    │
│   │ 06.07.2026 │  1,00  │ EUR  │ CAPTURED  │ 5O190127TN…        │    │
│   │ 06.07.2026 │  1,00  │ EUR  │ CREATED   │ 8AB12345CD…        │    │
│   └────────────┴────────┴──────┴───────────┴────────────────────┘    │
│                                                                      │
│   [ ← Back ]                                                          │
└──────────────────────────────────────────────────────────────────────┘
```

**Profile tab (read-only):**
```
┌─ Account settings ──────────────────────────────────────────────────┐
│ ╭ Profile ╮╭ Payment ╮                                               │
│ ┴─────────┘└──────────────────────────────────────────────────────  │
│    Username    edwin                                                 │
│    Name        Edwin Roth                                            │
│    Email       edwin.roth@gmx.at                                     │
│    Roles       MASTER_USER                                           │
│    Serial      TEST-0001                                             │
│    (read-only — edit users via Administration → Users)               │
│   [ ← Back ]                                                          │
└──────────────────────────────────────────────────────────────────────┘
```

**"Waiting for approval" modal (D6 polling handshake):**
```
┌─ Complete your payment ───────────────────────┐
│  A PayPal approval page opened in your        │
│  browser. Log in as the sandbox buyer and     │
│  approve the 1,00 € payment.                   │
│                                               │
│  When you've approved it there, click below.  │
│                                               │
│     [ I've approved — capture ]   [ Cancel ]  │
└───────────────────────────────────────────────┘
```

**End-to-end flow (who calls whom):**
```
User        PaymentTab        ServerClient        PaymentLogic/Server        PayPal(sandbox)
 │  Pay €1      │                  │                     │                        │
 │─────────────>│ createPayment(u) │                     │                        │
 │              │─────────────────>│  createPayment(u)   │                        │
 │              │                  │────────────────────>│ POST /v2/../orders     │
 │              │                  │                     │───────────────────────>│
 │              │                  │                     │<─ orderId + approveUrl ─│
 │              │                  │   write Tx=CREATED  │                        │
 │              │<─────────────────│<── {orderId,url,…} ─│                        │
 │  open approveUrl in system browser                    │                        │
 │──────────────────── approve as sandbox buyer ──────────────────────────────────>│
 │  click "I've approved"          │                     │                        │
 │─────────────>│ capturePayment(  │                     │                        │
 │              │   u, orderId)    │                     │                        │
 │              │─────────────────>│ capturePayment(…)   │                        │
 │              │                  │────────────────────>│ POST /orders/{id}/capture│
 │              │                  │                     │───────────────────────>│
 │              │                  │                     │<── CAPTURED + captureId │
 │              │                  │  update Tx=CAPTURED │                        │
 │              │<─────────────────│<── {status:CAPTURED}│                        │
 │  table shows CAPTURED row       │                     │                        │
```

### 4.4 PayPal developer setup (P0 — prerequisite, manual)
No PayPal account exists yet. Before any code runs end-to-end:
1. Create a **PayPal Developer** account at developer.paypal.com.
2. Create a **sandbox app** (REST) → obtain **Client ID** + **Secret** (sandbox).
3. Note the auto-created **sandbox business** account (the *recipient*/payee) and a **sandbox
   personal** account (the *payer* used to approve in the browser).
4. Put the values into the **external un-versioned config file**
   `/home/nidwe72/development/spectracs/spectracsPy-server-config/.env` (D4/OQ3). A **sketch already
   exists there** with every key + placeholder (`REPLACE_…`) — Edwin fills in the real values.

**Progress (2026-07-06):** **P0 done** — Edwin created the PayPal developer sandbox user + test
accounts, the config folder + `.env` sketch are in place, and Edwin has **filled the `.env`** with the
real Client ID / Secret / business-payee values. The only unverified bit is whether those creds
authenticate — that gets its first real test in **P2** (`getAccessToken()`).

### 4.4a `.env` keys (as sketched in `spectracsPy-server-config/.env`)
Only the **recipient** side + REST-app credentials — the **payer is never configured** (the buyer logs
into their own PayPal in the browser):

| Key | Purpose |
|-----|---------|
| `PAYPAL_ENV` | `sandbox` (→ `live` at go-live) |
| `PAYPAL_API_BASE` | `https://api-m.sandbox.paypal.com` |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` | REST-app creds → OAuth token |
| `PAYPAL_PAYEE_EMAIL` (or `PAYPAL_PAYEE_MERCHANT_ID`) | the **recipient** = sandbox *business* account |
| `PAYPAL_CURRENCY` / `PAYPAL_AMOUNT_MINOR` | `EUR` / `100` (= 1,00 €), server-authoritative |
| `PAYPAL_RETURN_URL` / `PAYPAL_CANCEL_URL` | required by Orders v2; placeholder pages fine (we poll) |

## 5. Implementation phases (when requested)

Ordered so each phase leaves the app runnable; UI (P3) depends on the server slice (P2).

| Phase | Repo / files | Change | Done-when |
|-------|--------------|--------|-----------|
| **P0 — PayPal setup** | (manual, external) | §4.4: dev account, sandbox app, client id/secret, sandbox business+personal accounts, server env vars. | Credentials exist server-side; `getAccessToken()` returns a token. |
| **P1 — Entity** | `spectracsPy-model` | `Transaction` + `TransactionStatusType` in `application/payment/`; register with server DB so `create_all` builds `transaction`. | Server DB has the table; a row can be inserted/queried in a scratch script. |
| **P2 — Server slice** | `spectracsPy-model` (logic) + `spectracsPy-server` (RPC) | `PayPalGateway` (token/create/get/capture, sandbox), `PaymentLogicModule` (create/capture/list), 3 `@expose` methods, client proxy mirrors. | A **headless script** (no UI) creates an order, prints the approval URL, and after manual sandbox-payer approval captures it → a `CAPTURED` `Transaction` row. **This is the verify gate.** |
| **P3 — UI** | `spectracsPy` | `AppUserSettingsViewModule` (Profile + Payment tabs), "Account settings…" menu action (desktop), nav registration. | From the running desktop app: account menu → Account settings → Payment tab → Pay €1 → approve in browser (sandbox personal) → back → capture → transaction appears `CAPTURED` in the table. |
| **P4 — Verify** | — (run app) | Drive-and-observe click-through (Edwin's review): logged-out (no entry), logged-in desktop (full flow), server-unavailable (graceful `ok:false`). | All §6 checks pass. |

### 5.1 Task breakdown (build-ready)

Granular per-phase steps with concrete files. `P0 ✓` done. Each phase leaves the app runnable; the
**P2 headless script is the gate** before any UI.

**P1 — `Transaction` entity** *(repo: `spectracsPy-model`)*
| # | File / artifact | Task |
|---|-----------------|------|
| P1.1 | `.../databaseEntity/application/payment/__init__.py` | new package |
| P1.2 | `.../application/payment/TransactionStatusType.py` | Enum `CREATED, APPROVED, CAPTURED, FAILED, CANCELLED` |
| P1.3 | `.../application/payment/Transaction.py` | entity on `ServerDbBaseEntity` + `DbBaseEntityMixin` (§4.1 columns) |
| P1.4 | server DB init (mirror how `AppUser` is imported) | ensure `Transaction` is imported before `create_all()` so the table is built |
| **Verify** | scratch script | insert + query a row in `spectracsPyServer.db`; confirm `transaction` (or `app_transaction`) table exists |

**P2 — Server slice** *(repos: `spectracsPy-model` logic + `spectracsPy-server` RPC + `spectracsPy` client)* — **the gate**
| # | File / artifact | Task |
|---|-----------------|------|
| P2.1 | `spectracsPy-server` startup (`service_pyro.py`/`main.py`) | load `spectracsPy-server-config/.env` at boot (dir via `SPECTRACS_SERVER_CONFIG_DIR`, fallback to the known path) |
| P2.2 | `spectracsPy-server/.../logic/payment/PayPalGateway.py` | `getAccessToken()` (+token cache, RD11), `createOrder(amountMinor,ccy,desc,payee)→(orderId,approvalUrl)`, `getOrder(id)`, `captureOrder(id)` |
| P2.3 | `spectracsPy-model/.../logic/payment/PaymentLogicModule.py` | `createPayment(userId)` (server sets amount, writes Tx=CREATED), `capturePayment(userId,orderId)` (capture→CAPTURED/else), `listTransactions(userId)`→`[dict]` |
| P2.4 | `spectracsPy-server/.../SpectracsPyServer.py` | 3 `@expose` thin delegators |
| P2.5 | `spectracsPy/.../logic/server/spectracs/SpectracsPyServerClient.py` | 3 mirror methods, defensive `{"ok":False,"message":"server unavailable"}` shape |
| P2.6 | `spectracsPy-server/.env.example` | committed, blank-value copy of the key list (§4.4a) + `.gitignore` for real `.env` |
| **Verify (GATE)** | headless script (no UI) | `createPayment` → print `approvalUrl` → approve in browser as sandbox **buyer** → `capturePayment` → a **CAPTURED** `Transaction` row. Proves creds + gateway + entity end-to-end. |

**P3 — UI** *(repo: `spectracsPy`)*
| # | File / artifact | Task |
|---|-----------------|------|
| P3.1 | `.../view/account/AppUserSettingsViewModule.py` (`QTabWidget`) | **Profile tab** (read-only current-user identity from `CurrentUserSession()`) |
| P3.2 | same | **Payment tab**: "Pay 1,00 € (sandbox)" button → `createPayment` → `QDesktopServices.openUrl` → poll modal → `capturePayment`; buttons disable during round-trip; not-approved keeps modal open |
| P3.3 | same | **Transactions `QTableWidget`** (date · amount · ccy · status · order id) from `listTransactions`, + ↻ refresh |
| P3.4 | de_AT formatting helper | `1,00 €` / `06.07.2026` display (storage stays minor units) |
| P3.5 | `.../view/main/MainStatusBarViewModule.py` | add **"Account settings…"** `QAction` above Logout in the logged-in **desktop** `QMenu` (Android branch unchanged) |
| P3.6 | `NavigationHandler` | register target `"AppUserSettingsViewModule"` (mirror `"UserListViewModule"`) |
| **Verify** | run desktop app | menu → Account settings → Payment → Pay → approve → capture → row appears |

**P4 — Verify / click-through** — §6 checklist (logged-out, logged-in flow, cancel, server-unavailable, secret-hygiene grep, `py_compile`).

## 6. Verification checklist (P4)

- Logged **out** → account button navigates to Login; **no** Account settings entry.
- Logged **in** (desktop) → account menu shows **Account settings…** above Logout → opens the tabbed
  screen; **Profile** shows the right user; **Payment** shows the Pay button + (initially empty)
  table.
- **Pay €1** → browser opens the sandbox approval page → approve as the **sandbox personal** payer →
  return to app → **[I've approved]** → status becomes **CAPTURED**, row appears (€1.00 · EUR ·
  CAPTURED · order id).
- **Cancel** in PayPal / don't approve → capture returns non-`CAPTURED`; row reflects
  `CANCELLED`/`FAILED`; UI shows a clear message, no crash.
- **Server unavailable** (stop the server) → Pay button surfaces "server unavailable", no crash.
- **Secret hygiene:** grep confirms no client id/secret in `spectracsPy` (client) or any committed
  file; only server env.
- `py_compile` clean across touched files.

## 7. Risks / open items

- **Secret leakage (highest).** D4 is load-bearing: the secret must never reach the client or a
  committed file. Verify in P4.
- **Return-URL / redirect capture.** D6 uses **polling** to sidestep needing a public `return_url`
  callback. PayPal still wants `return_url`/`cancel_url` on the order; point them at a simple
  info page (even a PayPal-hosted default) since we capture via polling, not via catching the
  redirect. Confirm sandbox accepts this during P2.
- **Amount tampering.** Amount is fixed **server-side** (D7); the client never sends it.
- **Idempotency / double-capture.** Capturing an already-captured order errors; `capturePayment`
  must treat "already captured" as success and not double-write. Use PayPal's `PayPal-Request-Id`
  header on create if we later retry.
- **Android.** Deferred (§1). The header menu is skipped on Android, and the browser round-trip needs
  an app-link/return-scheme — its own milestone.
- **Recurring €200 fee.** The actual product. Own spec (Subscriptions API: billing plan + product +
  subscription approval), built after this one-off flow is proven.
- **`Transaction` table name.** If `transaction` is quoted/reserved-awkward in SQLite, override to
  `app_transaction` (§4.1).
- **Currency/locale.** EUR hard-coded for milestone 1; generalise with the subscription milestone.

## 8. Milestone map (product view)

1. **M1 (this spec)** — single €1 sandbox payment, end-to-end, recorded + listed. *Proves the pipe.*
2. **M2** — recurring **€200/month** subscription (PayPal Subscriptions), pay-regardless-of-use.
3. **M3** — **live** credentials + go-live; receipts/invoicing.
4. **M4** — Android payment path.

## 9. Decisions resolved (was: open questions)  *(Edwin, 2026-07-06)*

| # | Question | **Decision** |
|---|----------|--------------|
| OQ1 | Who sees the Pay button — every logged-in user, or END_USER only? | **All logged-in users** in M1 (no role gate). Revisit with M2. |
| OQ2 | CANCELLED/FAILED reconciliation in M1, or only CREATED→CAPTURED? | **Only CREATED → CAPTURED** in M1. An un-approved order stays CREATED (RD5); full lifecycle with M2. |
| OQ3 | Where does the server read credentials? | The server has **no config mechanism today** → a **`.env` in an external un-versioned folder** `spectracsPy-server-config/` (outside all repos), loaded at server startup. Keys (see §4.4a): `PAYPAL_ENV`, `PAYPAL_API_BASE`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_PAYEE_EMAIL`/`PAYPAL_PAYEE_MERCHANT_ID`, `PAYPAL_CURRENCY`, `PAYPAL_AMOUNT_MINOR`, `PAYPAL_RETURN_URL`, `PAYPAL_CANCEL_URL`. Committed `.env.example` (blank values) in `spectracsPy-server` documents them. Dir located via `SPECTRACS_SERVER_CONFIG_DIR` (folder renamed 2026-07-06, typo fixed). |
| OQ4 | Amount/locale display — `€1.00` vs `1,00 €`? | **de_AT: `1,00 €`** (comma decimal, trailing € symbol). Amounts are still stored as integer minor units; only the *display* is localised (D7). |
| OQ5 | Profile tab in M1, or Payment-only? | **Include the read-only Profile tab** (my lean — makes the screen feel complete; cheap). |
| OQ6 | Test topology + outbound HTTPS to PayPal? | **Local server first**, then remote. `sciens.at` is an **AWS Lightsail Windows** instance → reaching `api-m.sandbox.paypal.com` is likely a **firewall/outbound rule** to open (RD7); sort that only when moving off local (P2/remote). |

## 10. Rubber-duck review

Adversarial read of the spec against the actual code/flow. ✅ = folded into the spec above; ◻ =
accepted known impl-time tune.

| # | Finding | Resolution |
|---|---------|-----------|
| RD1 | **Cross-base FK.** `ForeignKey("app_user.id")` only works if `Transaction` shares `AppUser`'s metadata. | ✅ Both are on `ServerDbBaseEntity` (same base, same `spectracsPyServer.db`) — FK is valid. §4.1 notes the target string must match `AppUser`'s real tablename (`app_user`). |
| RD2 | **UI could lie about the amount** if it hardcodes "€1.00" while the server sets the real value. | ✅ `createPayment` now returns `amountMinor`/`currency`; the client renders from the response (§4.2/§4.3). |
| RD3 | **User clicks "I've approved" before actually approving** → capture fails (order not APPROVED). | ✅ D6/§4.3: capture returns status; if not `CAPTURED`, modal stays open with a retry hint. |
| RD4 | **Double-capture** — double-click "I've approved" → PayPal errors on 2nd capture. | ✅ §4.3 disables the buttons during the round-trip; §7 keeps "already captured = treat as success". |
| RD5 | **Abandoned order stuck at CREATED** — closing the browser never sets CANCELLED. | ◻ OQ2: M1 intentionally only produces CREATED/CAPTURED; lifecycle reconciliation deferred to M2. |
| RD6 | **`QDesktopServices` import** path. | ◻ `from PySide6.QtGui import QDesktopServices` — noted in §4.3. |
| RD7 | **Server outbound reachability** — the Pyro host must reach `api-m.sandbox.paypal.com` over HTTPS. | ◻ OQ6 / §7: verify in P2 (outbound only — polling means no inbound callback needed). |
| RD8 | **Local vs remote credentials** — a locally-run dev server also needs the env vars. | ◻ OQ3: document that both topologies read the same env; never commit them. |
| RD9 | **`transaction` reserved-word** quirk in SQLite. | ✅ §4.1 fallback: override tablename to `app_transaction`. |
| RD10 | **`userId` trust** — the RPC takes a client-supplied `userId`; a caller could pass someone else's id to `listTransactions`. | ◻ Pre-existing pattern (all current RPCs pass `userId` as a param). Flagged as broader **auth debt** — a real system derives the user from an authenticated session, not a client arg. Not fixed in M1; noted for the auth hardening pass. |
| RD11 | **PayPal token re-fetch every call** wastes a round-trip (token lives ~9h). | ◻ Impl note: cache the access token in `PayPalGateway` with an expiry; minor. |
| RD12 | **Entity registration** — a new entity that isn't imported at DB-init won't get a table. | ✅ §4.1: register `Transaction` the same way `AppUser` is, so `create_all()` builds it. |

**Verdict:** design is sound and grounded — one new server-DB entity, one small gateway (two PayPal
endpoints), three thin RPCs + client mirrors, one new tabbed screen, one menu action. The load-bearing
risk is **secret hygiene** (D4); the rest are impl-time tunes or explicitly deferred (M2/auth pass).
The open questions (OQ1–OQ6) are decisions, not blockers — each has a sensible default. **Ready to
implement on explicit request.**

## 11. As-built — P1 + P2 (2026-07-06)

Backend implemented on explicit request ("impl P1+P2"). **UI (P3) deliberately not started** — stops
at the P2 gate so the first real sandbox payment can be watched before any widget exists.

### 11.1 Files created / changed
- **`spectracsPy-model`** (new):
  - `model/databaseEntity/application/payment/TransactionStatusType.py` — status enum.
  - `model/databaseEntity/application/payment/Transaction.py` — entity on `ServerDbBaseEntity`, FK
    `appUserId → app_user.id`, amount as integer minor units, `createdAt/updatedAt`. Table = `transaction`.
  - `logic/persistence/database/payment/PersistTransactionLogicModule.py` — save/update/findByOrderId/
    listByUser. **Imports `AppUser`** so the FK target is registered before `create_all()` (see 11.3).
  - `logic/config/ServerConfig.py` — stdlib `.env` loader (no python-dotenv). Resolves the config dir via
    `SPECTRACS_SERVER_CONFIG_DIR` or by walking up to the sibling `spectracsPy-server-config/`.
  - `logic/payment/PayPalGateway.py` — Orders v2 client over **stdlib `urllib`** (no `requests`/`httpx`;
    not in the app venv the server reuses). Token cache; `createOrder`/`getOrder`/`captureOrder`.
  - `logic/payment/PaymentLogicModule.py` — `createPayment`/`capturePayment`/`listTransactions`; amount
    server-authoritative; idempotent already-captured + "not approved yet" handling (RD3/RD4); plain-dict DTOs.
- **`spectracsPy-server`**: `SpectracsPyServer.py` +3 `@expose` lazy-delegating methods; `.env.example`
  (blank template); `.gitignore` gains `.env`; `verify_paypal_payment.py` (the interactive P2 gate).
- **`spectracsPy`**: `SpectracsPyServerClient.py` +3 defensive mirror methods.

### 11.2 Verified
- `py_compile` clean across all 9 touched files.
- **P1 self-test** (throwaway DB via `ANDROID_PRIVATE`): `transaction` + `app_user` tables build;
  save → findByOrderId → capture-update → listByUser all correct; `formatAmount(100)=="1.00"`.
- **P2 live sandbox:** `getAccessToken()` ✓ (real token) and `createOrder()` ✓ (real order id +
  approval URL) using Edwin's `.env`.
- **P2 GATE PASSED (Edwin, 2026-07-06):** ran `verify_paypal_payment.py`, approved as the sandbox
  personal buyer, order **captured** → `CAPTURED` Transaction recorded. Full create→approve→capture→
  persist path proven against the sandbox. (Browser landed on the `example.com` placeholder return URL
  after approval — expected; capture is by polling, not the redirect.)

### 11.3 Notes / deviations
- **FK registration order.** `Transaction.appUserId → app_user` only resolves at `create_all()` if
  `AppUser` is already imported. The server always seeds users at boot, but the transaction persistence
  module imports `AppUser` anyway so it is robust regardless of call order (a first self-test without it
  failed with `NoReferencedTableError`).
- **`.env` parser fix.** The first cut mis-parsed a *blank value followed by an inline comment*
  (`KEY=   # comment`) — it captured the comment as the value. Fixed: a `#` that starts the stripped
  value now yields empty. (`PAYPAL_PAYEE_MERCHANT_ID` was the trigger.)
- **Table name `transaction`** worked as-is in SQLite (no reserved-word quoting issue); the
  `app_transaction` fallback (§4.1) was not needed.
- **⚠ Open config item for the gate:** `PAYPAL_PAYEE_EMAIL` in the `.env` is currently a **personal**
  sandbox account; it must be the **business** account (recipient) or capture fails (cannot pay
  yourself). The personal account is the *buyer* used to approve in the browser.

### 11.4 Run the P2 gate
```
cd spectracsPy-server
PYTHONPATH=".:../spectracsPy:../spectracsPy-model:../spectracsPy-base" \
    ../spectracsPy/venv/bin/python verify_paypal_payment.py --username masterUser
```
Create → open the printed approval URL → log in as the **personal** sandbox buyer → approve → press
ENTER → capture → a `CAPTURED` `Transaction` row prints. That closes P2; P3 (UI) is next on request.

## 12. As-built — P3 UI (2026-07-06)

Built on explicit go ("go"). Milestone 1 is now feature-complete; only a human click-through of the
GUI payment round-trip remains.

### 12.1 Files created / changed
- **New** `spectracsPy/.../view/account/AppUserSettingsViewModule.py` — `PageWidget` with a `QTabWidget`:
  - **Profile tab** (read-only): Username, Roles, Registered serial, User id — from `CurrentUserSession`.
  - **Payment tab**: "Pay 1,00 € (sandbox)" button → `createPayment` → opens the approval URL via
    `QDesktopServices` → in-window "I've approved — capture" modal → `capturePayment`; a Transactions
    `QTableView` (Date · Amount · Status · PayPal order id) via `listTransactions`, plus a Refresh button.
    Buttons disable during each round-trip; "not approved yet" keeps things retryable.
  - Module-level `formatAmount`/`formatDate` = de_AT display (`1,00 €`, `06.07.2026 12:34`).
- **`InWindowDialog.py`** — new `choose(host, title, message, buttons)` static (custom-label chooser) for
  the approval modal.
- **`MainViewModule.py`** — import + add the screen at **stack index 16**.
- **`NavigationHandlerLogicModule.py`** — `"AppUserSettingsViewModule"` branch (title + index 16).
- **`MainStatusBarViewModule.py`** — "Account settings…" `QAction` above Logout in the logged-in
  **desktop** account menu (Android branch unchanged — no menu there, so desktop-only per §1).

### 12.2 Verified (offscreen / non-interactive)
- `py_compile` clean (all P3 files). Full app launches offscreen with **no tracebacks**.
- Screen builds at index 16 with 2 tabs; navigation target resolves; `formatAmount`/`formatDate` and the
  `TransactionsTableModel` render correctly; `__refresh` gives the right state logged-out (banner + Pay
  disabled, empty table) and logged-in (Pay enabled, profile populated, table filled — client stubbed).
- **Not covered:** the live GUI Pay→approve→capture round-trip (nested modal + browser + real sandbox) —
  that is Edwin's click-through.

### 12.3 Deviations from the design
- **Profile tab shows only session-available fields** (username/roles/serial/user id). Email + display
  name are **not** in `CurrentUserSession` and there is no single-user "get profile" RPC yet, so they are
  omitted rather than faked. Add a `getUserProfile` RPC later if the richer Profile is wanted.
- **Transactions table dropped the separate "Currency" column** (mockup §4.5 had one) — the Amount cell
  already renders the currency (`1,00 €`), so a Currency column was redundant.
- **"Not approved yet" retry = a fresh order** each time Pay is clicked (simpler than re-capturing the
  same order); fine for M1's one-off model.

### 12.4 Click-through — PASSED (Edwin, 2026-07-06)
Drove the running desktop app: logged in → account menu → **Account settings…** → **Payment** → **Pay
1,00 €** → approved in the browser as the sandbox personal buyer → **I've approved — capture** →
transaction shown **CAPTURED**. Milestone 1 complete.

---
*Milestone 1 DONE (implemented + click-through verified). Recurring billing (M2), live go-live (M3),
and Android (M4) are later milestones.*
