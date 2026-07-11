# SPEC — LIMS integration: create a Sample from the field app (SENAITE first, LIMS-agnostic)

Status: **IMPLEMENTED (2026-07-11)** — M1 built as phases L0–L7 and **click-through verified** on the dev bench
(driving Acquisition→Processing→Evaluation→Publishing + Publish created **OIL-0006** in SENAITE with the report PDF
attached). Design settled over three rubber-duck rounds; source: Edwin's SENAITE onboarding thread
(`~/Downloads/pumpkin/Google Gemini.html`) + the deferred §7 hook in
[`SPEC_bench_pdf_export.md`](SPEC_bench_pdf_export.md). Rode on **M2** (plugin-driven PDF).

## Status — what landed (2026-07-11)

L0 config (`LIMS_SENAITE_*` in `.env.example`) · L1 the LIMS-agnostic seam (`-model/logic/lims/`: neutral `dto/`,
`LimsGateway`, `LimsGatewayFactory`, `MockLimsGateway`) · L1-RPC server `@expose publishSampleToLims` + `LimsLogicModule`
(builds the neutral submission from the authenticated AppUser + spectrometer graph) + client wrapper · L2–L5
`SenaiteLimsGateway` (checkConnection, idempotent bottom-up ensure-or-create, createSample, attachPdf) verified live ·
L6 plugin `publishing()` + `LimsPublishView` + bench PUBLISHING step + `_PublishTab` Publish button + `pdfBytes()` · L7
click-through green. 23 offline tests (`test_lims_gateway_mock`, `test_lims_submission_assembly`,
`test_senaite_adapter_offline`). Live findings that shaped the adapter are in §5 "Live findings". Deferred items (§11)
unchanged.

## 1. The vision (field-to-lab), and what is in this repo

The DIY Spectracs unit measures **in the field**, produces the **M2 PDF** (visible report + embedded `workflow.json` +
named `capture_*.png`), and hands it to a **LIMS** — **SENAITE** first, but the design does **not** marry SENAITE
(§4). Two pieces, only the first is this repo:

1. **App → LIMS (this repo, Python).** A plugin-driven **PUBLISHING** step creates a **Sample** for the customer and
   attaches the PDF. ← **this milestone.**
2. **LIMS-side Plone add-on (separate codebase).** A custom SENAITE add-on that renders the PDF's embedded data on
   demand. Python 2.7 / Plone — **not this repo, deferred** (§11).

## 2. Architecture — **everything runs over the spectracsPy-server API**

The desktop client **never talks to the LIMS**. LIMS credentials never leave the server. The client calls **one Pyro
RPC**; the server holds the creds and does all LIMS I/O.

```
Publish button ─▶ spectracsPy-server RPC ─▶ LimsGateway (adapter) ─▶ LIMS API
   (client, Qt)       (@expose, Pyro)          (server-side)          (creds server-only)
```

- **Client (Qt app):** declares the step, **builds the M2 PDF** (only host with Qt/matplotlib — the server is
  headless), calls `publishSampleToLims(pluginLimsInfo, pdfBytes)`, shows the returned Sample ID.
- **Server:** resolves the authenticated **AppUser** and its **spectrometer graph** from its own DB to build the
  LIMS-neutral submission (§3), selects the LIMS adapter the plugin asked for (§4), runs the adapter, returns the ref.
  Reads creds from `.env` (server-only). Mirrors the PayPal precedent (secrets server-side, client calls an RPC).

### Sequence

```
Plugin        Host (client, Qt)     SpectracsServer          LimsGateway (adapter)     LIMS API
(PUBLISHING)  Wizard/Bench          @expose (Pyro)           e.g. SenaiteLimsGateway   (localhost:6090)
   │               │                     │                        │                       │
   │ declares step │                     │                        │                       │
   │ + Publish btn │                     │                        │                       │
   │──────────────▶│ (renders step-tab + [Publish])                │                       │
   │        user clicks [Publish]        │                        │                       │
   │               │─ build M2 PDF ─┐    │                        │                       │
   │               │  (WorkflowRpt) ◀┘   │                        │                       │
   │               │ publishSampleToLims(│                        │                       │
   │               │   pluginLimsInfo,   │                        │                       │
   │               │   pdfBytes) ───────▶│                        │                       │
   │               │                     │ AppUser + spectrometer  │                       │
   │               │                     │ graph → LimsSubmission   │                       │
   │               │                     │ pick adapter (plugin's   │                       │
   │               │                     │ LimsTarget), load .env   │                       │
   │               │                     │────────────────────────▶│ submit(submission)     │
   │               │                     │                        │── ensure/create ──────▶│
   │               │                     │                        │◀── uids ───────────────│
   │               │                     │                        │── create Sample ──────▶│
   │               │                     │                        │◀── OIL-0001 ───────────│
   │               │                     │                        │── attach PDF ─────────▶│
   │               │                     │◀── LimsSampleRef ───────│                       │
   │               │◀── {id, url} ───────│                        │                       │
   │        show "Logged to LIMS: OIL-0001"                        │                       │
```

## 3. The LIMS-neutral submission model (sourced from real domain entities)

A plain-Python, Pyro-serializable, **LIMS-agnostic** model in `spectracsPy-model/.../logic/lims/dto/`. It uses **our**
vocabulary — no SENAITE terms leak above the adapter. Three provenance sources:

```
LimsSubmission                         ← assembled SERVER-SIDE (+ pdfBytes on LimsReport)
│
├─ customer   : LimsCustomer   {code, name, contactFirst, contactLast, email}
│                              ← AppUser {username, displayName, firstName, lastName, email}      [server/DB]
│
├─ instrument : LimsInstrument {serial, model, manufacturer, kind, supplier}
│                              ← AppUser.registeredSerial → SpectrometerProfile → Spectrometer     [server/DB]
│                                serial       ← SpectrometerProfile.serial
│                                model        ← Spectrometer.modelName
│                                manufacturer ← SpectrometerVendor.vendorName
│                                kind         ← SpectrometerStyle.styleName  (fallback "Spectrometer")
│                                supplier     ← SpectrometerSensor.sellerName
│
├─ sampleType : LimsSampleType {name, code}                    ← PLUGIN  ("Pumpkin Oil" / "OIL")
├─ analyses[] : LimsAnalysis   {name, key, group}             ← PLUGIN  (M1: ONE generic service —
│                                                                 "Spectracs Measurement"/"SpectracsMeasurement";
│                                                                 per-metric analyses come later via a SENAITE plugin)
├─ sample     : LimsSample     {dateSampledIso, externalId}   ← workflow run
└─ report     : LimsReport     {pdfBytes, fileName}           ← CLIENT-built M2 PDF
```

**Why real entities matter:** the instrument is the actual registered spectrometer (vendor, model, style — not a
placeholder). **M1 is essentially a data upload** — the sample carries **one generic Analysis Service** as a placeholder
("Spectracs Measurement"); the *real* per-metric analyses (greenness / pigment / browning / clarity) and their
evaluation are handled **later by a SENAITE-side plugin** (§11, results-push). The neutral model already takes a *list*
of analyses, so promoting one → many is data, not a redesign.

**Client → server payload** is only the plugin's slice (`pluginLimsInfo` = sampleType + analyses + the `LimsTarget`,
§4) plus the PDF bytes. The customer + instrument are filled **server-side from the DB** so the client cannot spoof
identity.

## 4. LIMS abstraction — one seam, an adapter per LIMS, plugin selects the target

There is **no existing Python library** that abstracts sample-creation across LIMS products (the standards — SiLA 2,
AnIML, HL7/ASTM — are instrument-control / data-exchange formats, not a registration API). So we own a thin seam:

```
class LimsGateway(Protocol):
    def checkConnection(self) -> LimsHealth: ...          # base URL reachable + auth ok
    def submit(self, submission: LimsSubmission) -> LimsSampleRef: ...   # {id, url}

registry (LimsGatewayFactory):  backend id ─▶ adapter
    "senaite"  ─▶ SenaiteLimsGateway   (jsonapi; ensure-or-create graph → AnalysisRequest → attach)  ← M1
    "mock"     ─▶ MockLimsGateway      (records the call; for tests / offline dev)                    ← M1
    "openelis" ─▶ (future, FHIR/HL7)

plugin selects:  plugin.getLimsTarget() -> LimsTarget(backend="senaite", configKey="SENAITE")
server:  gw = LimsGatewayFactory.create(plugin.getLimsTarget())   # picks adapter + loads .env by configKey
         ref = gw.submit(submission)
```

- **Only the adapter knows its LIMS.** `LimsSubmission` and everything upstream (plugin, server assembly) are
  LIMS-agnostic. Swapping/adding a LIMS = write one adapter + register it; nothing else moves.
- **The plugin chooses** via a tiny `LimsTarget` (backend id + config key) exposed through `plugin_sdk`. (Making the
  target master-configurable per `SpectrometerSetup` is a later refinement; plugin-declared is the M1 answer.)
- **`MockLimsGateway`** lets L-phases + tests run with no live Docker.

## 5. What the SENAITE adapter does — full bootstrap, ensure-or-create, bottom-up

`SenaiteLimsGateway.submit()` maps the neutral submission onto SENAITE's object graph. A **Sample**
(internally `AnalysisRequest`) mandatorily references pre-existing objects, several with their own required-reference
sub-chains. The adapter **bootstraps the whole graph** — every object **idempotent** (search by a stable key first,
create only if absent); on a warmed-up lab it collapses to search-hits + `create Sample` + `attach`. No cross-call
transaction — **safe retry rides on idempotency** (a re-run re-finds everything).

**Creation order (leaves first) & neutral-field source:**

```
        ┌──────────────┐        ┌──────────────┐   ┌────────────┐   ┌───────────┐
        │  Department  │        │InstrumentType│   │Manufacturer│   │  Supplier │
        │  (const)     │        │ ← kind       │   │ ← manufac. │   │ ← supplier│
        └──────┬───────┘        └──────┬───────┘   └─────┬──────┘   └─────┬─────┘
               ▼                       └──────────────┬──┴────────────────┘
        ┌──────────────┐                              ▼
        │AnalysisCateg.│                       ┌────────────┐  SerialNo ← instrument.serial
        │ ← group      │                       │ Instrument │  (audit identity; analysis-level
        └──────┬───────┘                       └────────────┘   link deferred to results-push)
               ▼
        ┌──────────────┐   ┌────────────┐
        │AnalysisServ. │   │ SampleType │  ← sampleType.name/code
        │ ← analyses[] │   └─────┬──────┘
        └──────┬───────┘         │        ┌────────┐  ClientID ← customer.code, title ← customer.name
               │                 │        │ Client │
               │                 │        └───┬────┘
               │                 │            ▼
               │                 │        ┌─────────┐  ← customer.contactFirst/Last/email
               │                 │        │ Contact │
               │                 │        └───┬─────┘
               └───────┬─────────┴────────────┘
                       ▼
               ┌───────────────┐
               │ Sample (AR)   │──▶ attach PDF (Attachment)
               │  OIL-0001     │
               └───────────────┘
```

| # | SENAITE object | `portal_type` / parent | Key create fields | Idempotency key |
|---|---|---|---|---|
| 1 | Department | `Department` @ setup/departments | `title` (const, e.g. "Lab") | title |
| 2 | AnalysisCategory | `AnalysisCategory` @ …/analysiscategories | `title` ← analysis.group, `Department=<uid#1>` | title |
| 3 | AnalysisService | `AnalysisService` @ …/analysisservices | `title` ← analysis.name, `Keyword` ← analysis.key, `Category=<uid#2>` | **Keyword** |
| 4 | SampleType | `SampleType` @ …/sampletypes | `title` ← sampleType.name, `Prefix` ← sampleType.code | Prefix/title |
| 5 | InstrumentType | `InstrumentType` @ …/instrumenttypes | `title` ← instrument.kind | title |
| 6 | Manufacturer | `Manufacturer` @ …/manufacturers | `title` ← instrument.manufacturer | title |
| 7 | Supplier | `Supplier` @ …/suppliers | `title` ← instrument.supplier | title |
| 8 | **Instrument** | `Instrument` @ …/instruments | `title="<model> <serial>"`, `SerialNo` ← serial, `Model` ← model, `InstrumentType/Manufacturer/Supplier=<uids>` | **SerialNo** |
| 9 | **Client** | `Client` @ /senaite/clients | `title` ← name, `ClientID` ← code | **ClientID** |
| 10 | **Contact** | `Contact` @ …/`<client>` | `Firstname`, `Surname`, `EmailAddress` | Firstname+Surname (under client) |
| 11 | **Sample** | `AnalysisRequest` @ `create` | `parent_uid=<#9>`, `Contact=<#10>`, `SampleType=<#4>`, `DateSampled`, `Analyses=<#3…>` | (always — the new job) |
| 12 | Attach PDF | `Attachment` under the sample | `AttachmentFile=<pdf bytes>`, filename | (always) |

**M1 supplies a single generic Analysis Service** ("Spectracs Measurement" / keyword `SpectracsMeasurement`, category
"Spectroscopy", department "Lab") — the milestone is *data upload*; the real per-metric analyses + their evaluation land
later in the SENAITE-side plugin (§11). The table iterates `analyses[]`, so this is just a one-element list today.

Setup-folder paths differ across SENAITE 2.x (`bika_setup/…` vs `setup/…`); the adapter resolves each container's UID
by a one-time catalog search, not a hard-coded path. **Instrument nuance:** an `AnalysisRequest` has no top-level
Instrument field — SENAITE links instruments at the analysis/worksheet/result-import level, so M1 only **ensures the
Instrument exists** (by serial); associating it to analyses is deferred to results-push (§11).

### Live findings (L2–L5, verified against the 6090 Docker, 2026-07-11)

Building the adapter against the real instance corrected several assumptions — captured here so the next
session doesn't re-derive them:
- **Container paths are mixed:** most setup types live under `/senaite/setup/…`, but **`AnalysisService` and
  `Instrument` are under the legacy `/senaite/bika_setup/bika_…`**. Hard-coded in `SenaiteLimsGateway.CONTAINERS`.
- **`AnalysisService` needs no category**, and **`AnalysisRequest` doesn't hard-require analyses** → the whole
  `Department → AnalysisCategory` chain is skipped (Department also required a `manager` LabContact — avoided).
- **`AnalysisService` create returns an error body** (`success:false`, `'NoneType'.form`) **but the object
  persists.** So ensure-or-create must **create-then-resolve-by-search**, never trust the create response's uid.
  `_ensureItem` does exactly this (idempotent, title exact-match in Python — the title index is fuzzy).
- **Required fields (this instance):** `SampleType` → `prefix` + `min_volume`; `Client` → `Name` + `ClientID`;
  `Instrument` → title + `InstrumentType`/`Manufacturer`/`Supplier` (uids).
- **`DateSampled` must be date-only** (`YYYY-MM-DD`) — a full timestamp trips SENAITE's "after now" validation
  against the container clock.
- **Attachments:** created under the **Client** (not the sample — "not allowed"), `AttachmentFile` = a **plain
  base64 string** (dict/data-uri forms → "Incorrect padding"), `filename` as a top-level key. The AR↔attachment
  link is set via `/update`-ing the sample's `Attachment` list; **this jsonapi build does not read the link
  back**, so it must be eyeballed on the sample's Attachments tab (open item).
- The service account has role **Manager** (verified via `users/current`) — full create rights.

## 6. The `senaite.jsonapi` transport (confirmed vs the 2.x doctests)

- **Base:** `http://<host>:<port>/senaite/@@API/senaite/v1` — Edwin maps **`6090:8080`**, site `/senaite`
  → `http://localhost:6090/senaite/@@API/senaite/v1`.
- **Auth:** HTTP **Basic**, the manually-created **`spectracs_app_service`** (§8). Server-side only.
- **Resolve key → UID:** `GET …/search?portal_type=<T>&<key>=<value>` → `items[]` with `uid`.
- **Create (generic):** `POST …/create`, verbatim shapes: `Client` = `portal_type,parent_path,title,ClientID`;
  `Contact` = `portal_type,parent_path,Firstname,Surname`; `AnalysisRequest` =
  `portal_type,parent_uid,Contact,SampleType,DateSampled,Analyses(repeatable)`. **All refs by UID.**

## 7. Config (server-side `.env`, keyed by backend)

Via the existing `ServerConfig` mechanism (external `../spectracsPy-server-config/.env`), documented in
`spectracsPy-server/.env.example`. Keyed by the adapter's `configKey` so several backends coexist:

```
LIMS_SENAITE_BASE_URL=http://localhost:6090/senaite/@@API/senaite/v1
LIMS_SENAITE_USER=spectracs_app_service
LIMS_SENAITE_PASSWORD=
```

The factory reads `LIMS_<configKey>_BASE_URL/_USER/_PASSWORD`. Matches the PayPal precedent
(`SPEC_paypal_payment.md` §4.4).

## 8. The `spectracs_app_service` — manual setup, and the permission tension

**Decision: the field-service user is created manually in SENAITE by the master/admin** (see the guide in the README/
ops notes). Two forces meet here, and the resolution shapes M1:

- Full **bootstrap** (§5) creates *setup/master-data* objects (Department, AnalysisService, SampleType, Instrument
  types…). In SENAITE that needs **Lab Manager** rights — a minimal "Add Sample + Add Attachment" user **cannot** create
  setup objects.
- Edwin's deployment for M1 is a **single, self-owned local SENAITE** (his own Docker). There a Lab-Manager-grade field
  user is acceptable — it is the owner's own lab.

**M1 recommendation:** create `spectracs_app_service` with the **Lab Manager** role → full runtime bootstrap works. For a future
**multi-tenant / central lab**, invert it: pre-provision master-data once with admin, and give `spectracs_app_service` a minimal
custom role (Add Client/Contact/Sample/Attachment only) — the same adapter code then simply finds the master-data by
search instead of creating it (idempotency makes this transparent). This is a **role choice at setup time, not a code
change.**

## 9. Rubber-duck — remaining validation points (handled at impl)

- **No resolvable instrument** (AppUser has no `registeredSerial` / no profile → e.g. some master accounts): the server
  must **fail Publish with a clear message** ("no spectrometer bound to this user"), not silently create a blank
  instrument. Validate before calling the adapter.
- **Virtual devices** (`SpectrometerSensor.isVirtual`): a virtual run still yields a valid Instrument keyed by its
  (seeded) serial — acceptable and useful for testing; no special-casing, just noted.
- **Partial failure**: no cross-call transaction; a failed Sample-create after some master-data was created leaves
  reusable objects — a retry re-finds them (idempotent). Surface the failing step.
- **Connectivity/config**: `checkConnection()` runs first (or on step entry) so a bad URL / wrong creds / offline shows
  as a clear status, consistent with the online-required product model.
- **`ClientID` stability**: derive from `username` (stable), not `displayName` (mutable) — a display-name change must
  not spawn a duplicate Client.

## 10. Impl plan (L-phases)

| Phase | Scope | Key artifacts | Done when |
|---|---|---|---|
| **L0** | deps + config | `LIMS_SENAITE_*` in `.env.example`; choose HTTP lib (prefer stdlib `urllib`) | `ServerConfig` resolves the keys; documented |
| **L1** | the **abstraction seam** (LIMS-agnostic) | `dto/` neutral model (`LimsSubmission`, `LimsCustomer/Instrument/SampleType/Analysis/Sample/Report`, `LimsSampleRef`); `LimsGateway` protocol; `LimsGatewayFactory`; `LimsTarget`; **`MockLimsGateway`** | a hand-built submission runs through the mock end-to-end; unit-tested with no Docker |
| **L1-RPC** | server RPC + submission assembly | `@expose publishSampleToLims(pluginLimsInfo, pdfBytes)` on `SpectracsPyServer`; server builds `LimsSubmission` from the **authenticated AppUser + spectrometer graph** (§3); client wrapper | client calls the RPC; server logs a fully-populated neutral submission; instrument = real registered spectrometer |
| **L2** | SENAITE adapter — connection + search | `SenaiteLimsGateway.checkConnection()` + `search(portal_type,key)→uid` against local `6090` | resolves a demo object's UID; bad creds → clear health error |
| **L3** | adapter — bootstrap master-data (§5 #1–7) | idempotent ensure-or-create: Department, Category, AnalysisService, SampleType, InstrumentType, Manufacturer, Supplier | re-run finds existing UIDs (no dupes); first run creates them (needs Lab-Manager `spectracs_app_service`, §8) |
| **L4** | adapter — instrument + customer (§5 #8–10) | ensure Instrument (by serial), Client (by ClientID), Contact | the registered spectrometer + customer appear in SENAITE, keyed correctly |
| **L5** | adapter — create Sample + attach (§5 #11–12) | `createSample` (AnalysisRequest) + `attachPdf`; return `LimsSampleRef` | new Sample ID (`OIL-0001`) visible; Attachments tab shows the PDF; `pdfdetach` still lists `workflow.json` + captures |
| **L6** | plugin PUBLISHING step | plugin declares PUBLISHING phase + "Send to LIMS" step + **Publish** button + `getLimsTarget()` + its sampleType/analyses; client builds PDF, calls RPC, shows ID | driving the plugin to the last phase + Publish creates the Sample + attaches the PDF; ID shown |
| **L7** | verify + robustness | end-to-end on local `6090`; idempotent re-publish; the §9 validations (no-serial, offline, partial-failure) | one clean round-trip, no dupes on re-publish, graceful failures |

Notes: L1+L1-RPC are LIMS-agnostic and testable via the mock **before** any SENAITE work (L2+). The permission choice
(§8) only bites at **L3** — with a Lab-Manager `spectracs_app_service` the bootstrap self-heals a blank lab; with a minimal user,
master-data must pre-exist.

## 11. Deferred (not this milestone)

- **LIMS-side Plone add-on** — PDF viewer + on-demand spectrum render inside SENAITE (separate repo, Plone/Py2.7).
- **Results push + real per-metric analyses + analysis-level Instrument link** — replace M1's single generic service
  with the real peak-ratio metrics as Analysis Services, post their values, and bind the Instrument at analysis level;
  the **SENAITE-side plugin** owns evaluation. Needs the P5 real-oil thresholds.
- **Sample state machine** — Receive → Submit → Verify → Publish (CoA). M1 only *creates*.
- **Field reliability** — offline queue + retry, MD5 checksum, `Field_App_Sync_Status`.
- **Master-configurable LIMS target** — move `LimsTarget` from plugin-declared to per-`SpectrometerSetup` config.
- **Second adapter** (e.g. OpenELIS/FHIR) — proves the seam.

## 12. Facts / references

- SENAITE = Docker `senaite/senaite:v2.6.0`, Plone 5.2 / **Python 2.7**; Edwin maps `-p 6090:8080`. `--rm` wipes data
  unless a Docker volume is mounted.
- No cross-LIMS abstraction library exists; standards (SiLA 2, AnIML, HL7/ASTM) are instrument/data-level → we own a
  thin `LimsGateway` seam.
- `senaite.jsonapi` create/search confirmed vs the **2.x doctests** (`…/tests/doctests/create.rst`) + `api.html`.
- Real domain entities: `Spectrometer.modelName`; `SpectrometerVendor.vendorName`; `SpectrometerStyle.styleName`;
  `SpectrometerSensor.sellerName`; `SpectrometerProfile.serial`; `SpectrometerSetup → {SpectrometerProfile, DbPlugin}`;
  `AppUser{username, displayName, email, firstName, lastName, registeredSerial}`.
- Config precedent: `SPEC_paypal_payment.md` §4.4 (same `ServerConfig` / external `.env`).
