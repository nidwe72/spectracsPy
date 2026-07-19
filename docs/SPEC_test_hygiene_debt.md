# SPEC — Hygiene debt (pre-existing, non-blocking defects)

Status: **BACKLOG — not blocking any feature.** Catalogues known defects that are real but gate nothing —
each with its root cause and the fix, so they are **tracked rather than rediscovered every run**.

**Scope widened 2026-07-17** from test-only (`T*`) to also cover **runtime** debt (`R*`) and **doc drift** (`D*`).
The trigger: the S0–S4 tiering work re-found **T1 and T2 from scratch** and wrote them into
[`SPEC_project_structure.md`](SPEC_project_structure.md) a second time — exactly what this file exists to prevent.
It only works if it is the single place, and if it is read before declaring something "pre-existing".
Surfaced 2026-07-10 during the M2 (PDF report) verification sweep — **none are caused by M2**; all three predate
it and live in code M2 never touches (confirmed by the M2 diff having zero overlap with the implicated files).

> **UPDATE 2026-07-19 — the suite no longer hangs.** T2 (the staller) is fixed and a per-test hang watchdog
> (`tests/conftest.py`) now guards against the next one, so `pytest tests/` runs whole:
> ```
> QT_QPA_PLATFORM=offscreen PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
>     ./venv/bin/python -m pytest tests/ -q
> ```
> → **192 passed in ~25s.** The old per-file-with-timeout workaround is no longer needed (kept below for history).
>
> **Why this file exists:** it is the single place known defects are tracked so they are not rediscovered from
> scratch every run. Read it before declaring anything "pre-existing".

## Snapshot (2026-07-19) — CURRENT: all test items CLEARED ✅

Whole-suite `pytest tests/` (offscreen, full `PYTHONPATH` incl. `-core`, `-server`, `spectracs-plugins`):
**192 passed in ~25s, no hang.** Every catalogued test item (T1–T4) is now resolved.

| Item | Test file | Was | Now |
|---|---|---|---|
| **T1** | test_plugin_binding_and_seed | 5 errors (stale calib-DB fixture) | ✅ 6 passed |
| **T2** | test_workflow_wizard_persistence_offscreen | 🔴 modal-dialog hang (suite-staller) | ✅ fixed (right dialog patched) + watchdog |
| **T3** | test_pumpkin_wizard_offscreen | 1 failed (stale nav-glyph) | ✅ 1 passed |
| **T4** | test_lims_submission_assembly | 1 failed (manufacturer default) | ✅ 6 passed (test fixed to `"Spectracs"`) |

**History:** T1 & T3 were fixed incidentally (T1 by the Alembic/AllEntities `create_all`-from-live-metadata work;
T3 by a glyph-assertion update). T2 & T4 were fixed on 2026-07-19 as this pass (details in each section below).
T4 never appeared in the 2026-07-10 snapshot — the LIMS test file postdates it, and it had failed since birth
(code + test landed inconsistent in the M1 LIMS work).

Remaining catalogued debt is now **runtime/doc only** (R1, R2, D1 below) — no test items open.

<details><summary>Historical snapshot (2026-07-10, per-file run — superseded)</summary>

| Test file | Result | Item |
|---|---|---|
| test_plugin_sdk_ops | ✅ 5 passed | |
| test_spectrum_processing | ✅ 11 passed | |
| test_workflow_persistence | ✅ 1 passed | *(exercises the M2-reworked `EvaluationResult` serialization — backward-compatible)* |
| test_virtual_device_image_roundtrip | ✅ 2 passed | |
| test_pumpkin_oil_spectrum_to_color_eval | ✅ 10 passed | |
| test_step_bar_widget_offscreen | ✅ 2 passed | |
| test_stale_calibration_recovery | ✅ 2 passed | |
| test_pumpkin_workflow_end_to_end | ✅ 3 passed | |
| **test_plugin_binding_and_seed** | ⚠️ 5 errors | **T1** |
| **test_workflow_wizard_persistence_offscreen** | ⚠️ timeout (hang) | **T2** |
| **test_pumpkin_wizard_offscreen** | ⚠️ 1 failed | **T3** |

</details>

---

## T1 — `test_plugin_binding_and_seed`: stale test-DB schema  ✅ RESOLVED (2026-07-19)
**Symptom (at fixture *setup*, all 5 tests error before any logic):**
```
sqlite3.OperationalError: table spectrometer_calibration_profile has no column named calibrationSpectrumJson
```
**Root cause:** the test builds its SQLite schema from a fixture/snapshot that predates the
`SpectrometerCalibrationProfile.calibrationSpectrumJson` column added to the model. The mapper emits an INSERT
with the new column; the fixture table lacks it. Pure **schema drift** in the test fixture — not a product bug.

**Fix (DONE):** the test schema now builds from current mapped metadata, so the column can't drift out again.
Verified 2026-07-19: `test_plugin_binding_and_seed` = **6 passed**. **Effort was:** small (test-fixture only).

## T2 — `test_workflow_wizard_persistence_offscreen`: blocks on a modal dialog (the suite-staller)  ✅ RESOLVED (2026-07-19)
**Symptom (was):** the whole-suite run hung indefinitely here (0 bytes of buffered output). Fault-handler stack
(exact line numbers):
```
test_new_run_saves_then_view_edits_then_delete (test…:119)
  → WizardViewModule.onClickedDelete (570) → __deleteWorkflow (602)
  → InWindowDialog.confirm (108) → InWindowDialog.__run (96)   (blocked — own event loop, nobody clicks)
```
**Root cause:** the delete path opens a **modal in-window confirm dialog** (`InWindowDialog.confirm`) that spins
its own nested event loop waiting for a button click. Headless, nobody clicks → it blocks forever. The test
*tried* to auto-accept but patched **`QMessageBox.question`** — the **wrong dialog** (the delete path never calls
it), so the patch was a silent no-op. A test-harness gap, not a product defect.

**Fix (DONE, 2026-07-19):**
1. The test now patches the **right** target — `InWindowDialog.confirm` → auto-returns `True` for the delete
   step (was patching `QMessageBox.question`, a no-op). The dropped `QMessageBox` import went with it.
2. **Safety net for the next one:** `tests/conftest.py` arms a per-test **faulthandler watchdog** (120s budget,
   autouse) that dumps all-thread stacks and aborts if any single test overruns — so a future modal-in-test
   fails FAST naming the culprit instead of silently hanging the suite. **Chosen over `pytest-timeout`
   deliberately:** the project has no pytest config and the plugin isn't installed; a `--timeout` option absent
   the plugin would itself break the run in any bare environment. The watchdog is dependency-free (stdlib only).

Verified 2026-07-19: `pytest tests/` (whole suite) = **192 passed in ~25s, no hang**.

## T3 — `test_pumpkin_wizard_offscreen`: nav-glyph assertion mismatch  ✅ RESOLVED (2026-07-19)
**Symptom (was):**
```
AssertionError: 'Next →' != 'Next ▶'
```
**Root cause:** the wizard's Next-button label glyph changed (`→` vs `▶`) but this assertion still expected the
old glyph. Cosmetic/stale-assertion — the button always worked. **Fix (DONE):** the expected string was updated
to the shipping glyph. Verified 2026-07-19: `test_pumpkin_wizard_offscreen` = **1 passed**. **Effort was:** trivial.

## T4 — `test_lims_submission_assembly`: manufacturer/supplier fallback expectation  ✅ RESOLVED (2026-07-19)
**Symptom (was):**
```
test_missing_vendor_sensor_are_blank_not_crash
  AssertionError: 'Spectracs' != ''   (submission.instrument.manufacturer)
```
**Root cause:** the test feeds an *absent* vendor/sensor (`_setup(vendor=None, sensor_seller=None)`) and asserts
the LIMS instrument fields come out **blank** (`""`). But `LimsLogicModule.buildSubmission` (lines 76–83)
deliberately substitutes a non-empty house label so SENAITE never receives blank-title master data:
```python
# Fall back to non-empty labels so the LIMS never gets blank-title master data …
manufacturer=(vendor.vendorName if vendor is not None else "") or "Spectracs",
supplier   =(sensor.sellerName if sensor is not None else "") or "Spectracs")
```
→ missing vendor yields `"Spectracs"`, not `""`. **Born inconsistent:** the code (`80f770e`) and the test
(`ead83d7`) both landed in the M1 LIMS work with opposite expectations, so this test has failed since its first
commit. It escaped the 2026-07-10 snapshot only because the whole LIMS test file postdates that snapshot. This
is **pure test-side drift**, not a product bug (nothing consumes the blank-vs-`"Spectracs"` behaviour but the test).

**Decision (Edwin, 2026-07-19):** the **code is right, the test is wrong** — fix the test to expect `"Spectracs"`.
Rationale: a spectrometer's vendor must **always** be set; a missing vendor is corrupt data we do not want to
surface, and a blank Manufacturer in the LIMS is exactly that exposure — the non-empty fallback prevents it.
`"Spectracs"` is a legitimate manufacturer name (Spectracs is also the hardware maker, so it is not a misleading
stand-in). **Fix (DONE):** `test_missing_vendor_sensor_are_blank_not_crash` renamed to
`test_missing_vendor_sensor_default_not_blank`, now asserts `manufacturer == "Spectracs"` and
`supplier == "Spectracs"`, with the invariant recorded in a comment. Code unchanged. Verified 2026-07-19:
`test_lims_submission_assembly` = **6 passed**. **Note:** the LIMS unit tests need **no** live SENAITE —
`buildSubmission` is pure assembly and the round-trip test uses `MockLimsGateway`; the real SENAITE path is
exercised only by the manual runbook (SPEC_lims_integration.md §12.1), kept out of the suite on purpose.

---

## R1 — the server cannot find a LAN IP on modern interface names (found 2026-07-17)

`./runServer.sh` dies with an opaque `TypeError: argument must be an int, or have a fileno() method` at
`spectracsPyServer.py:94`. **Nothing to do with the tiering** — it reproduces identically with and without
`spectracsPy-core` on the path, and the server repo is untouched.

The cascade, every step confirmed from Edwin's own output:

```
  NetworkUtil.getLocalIpAddress()  ->  None        <- the bug: it matches only 'wlp*' or 'eth0*'
        |
  NAMESERVER_HOST='LOCAL' -> resolves to None      ->  appliedArgs shows nameserverHost: None
        |
  Pyro5.api.start_ns(host=None)  ->  binds LOOPBACK  ->  "PYRO:Pyro.NameServer@localhost:8090"
        |
  Pyro5 REFUSES a broadcast server on loopback     ->  returns broadcastServer = None
        |
  rs=[None] -> select.select([None],...)           ->  TypeError, 20 lines from the cause
```

**Root cause:** `NetworkUtil.getLocalIpAddress()` (`spectracsPy-base`) hardcodes `startswith('wlp')` (WiFi) and
`startswith('eth0')` — the *old* kernel naming. Modern systemd predictable names are `eno1` / `enp3s0` / `ens…`,
which match neither. Edwin's wired interface is **`eno1`**, so on wired it finds nothing; it presumably worked on
WiFi (`wlp*`). Triggered by a network switch.

**Fix (two parts, both small):**
1. `NetworkUtil`: accept the `en*` family (`eno`, `enp`, `ens`, `enx`) alongside `wlp`/`eth`. Skip virtual
   interfaces — this machine also has `virbr0`, `docker0`, `vmnet1`, `vmnet8`, `tun_vpn`, and picking one of those
   would be worse than picking none.
2. `spectracsPyServer.py`: **guard `broadcastServer is None`** before putting it in the `select()` list. Pyro5
   documents returning `None` on loopback, so this is a supported state, not an error — but the missing LAN IP
   should fail *loudly at startup*, not as a `TypeError` in the event loop.

**Workaround (verified working by Edwin, 2026-07-17):** pass the host explicitly —
`./runServer.sh --nameserverHost=192.168.1.223 --daemonHost=192.168.1.223`.

## R2 — `runServer.sh` has no `spectracsPy-core` on PYTHONPATH (found 2026-07-17)

```
export PYTHONPATH=".:../spectracsPy:../spectracsPy-model:../spectracsPy-base"
```

**Mine.** S3b's phase-0 sweep taught 26 files the `-core` path but ran over `git ls-files` **inside `spectracsPy`
only**, so it never reached the sibling repos. It did **not** cause R1 (proven: identical crash with `-core` on the
path) and has not bitten yet — but the server imports app code, and app code reaches into `-core`, so it is a live
trap. **Fix:** add `../spectracsPy-core`. Check the other sibling repos for the same omission while there.

## D1 — `SPEC_spectrum_processing.md` §174 calls `luxpy` dead; it is live again (found 2026-07-17)

§174 lists `luxpy` as **"drop — dead code"**. That referred to `spd(...)`/`spd_to_xyz(...)` in `SpectrumToColor`,
since removed. But `synthesis/SpectrumSynthesisUtil` now uses `luxpy.toolboxes.spdbuild.gaussian_spd` for the
**390–410 nm UV-A LED** (no measured Avonec curve exists there), with a plain-Gaussian fallback. Harmless while
everything shares one venv; misleading to anyone trimming dependencies. **Fix:** correct §174.

## Not in scope
Product behaviour — all three are test-side (stale fixture, un-driven modal, stale assertion). No application code
change is implied. Fixing them is worthwhile hygiene (a green, non-hanging `pytest tests/`) but gates nothing.
</content>
