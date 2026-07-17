# SPEC — Hygiene debt (pre-existing, non-blocking defects)

Status: **BACKLOG — not blocking any feature.** Catalogues known defects that are real but gate nothing —
each with its root cause and the fix, so they are **tracked rather than rediscovered every run**.

**Scope widened 2026-07-17** from test-only (`T*`) to also cover **runtime** debt (`R*`) and **doc drift** (`D*`).
The trigger: the S0–S4 tiering work re-found **T1 and T2 from scratch** and wrote them into
[`SPEC_project_structure.md`](SPEC_project_structure.md) a second time — exactly what this file exists to prevent.
It only works if it is the single place, and if it is read before declaring something "pre-existing".
Surfaced 2026-07-10 during the M2 (PDF report) verification sweep — **none are caused by M2**; all three predate
it and live in code M2 never touches (confirmed by the M2 diff having zero overlap with the implicated files).

> **Why this exists:** running `pytest tests/` as a whole **hangs** (one test blocks on a modal dialog, see T2),
> which masks the real pass/fail picture. Until T2 is fixed, run **per-file with a timeout**:
> ```
> for t in tests/test_*.py; do timeout 120 ./venv/bin/python -m pytest "$t" -q; done
> ```
> (with `QT_QPA_PLATFORM=offscreen` and the usual `PYTHONPATH`).

## Snapshot (2026-07-10, per-file run)

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

---

## T1 — `test_plugin_binding_and_seed`: stale test-DB schema
**Symptom (at fixture *setup*, all 5 tests error before any logic):**
```
sqlite3.OperationalError: table spectrometer_calibration_profile has no column named calibrationSpectrumJson
```
**Root cause:** the test builds its SQLite schema from a fixture/snapshot that predates the
`SpectrometerCalibrationProfile.calibrationSpectrumJson` column added to the model. The mapper emits an INSERT
with the new column; the fixture table lacks it. Pure **schema drift** in the test fixture — not a product bug.

**Fix:** rebuild the test schema from the current mapped metadata (`Base.metadata.create_all` against the model)
instead of a frozen DDL, or add the missing column to the fixture. Prefer regenerating from metadata so it can't
drift again. **Effort:** small (test-fixture only).

## T2 — `test_workflow_wizard_persistence_offscreen`: blocks on a modal dialog (the suite-staller)
**Symptom:** the whole-suite run hangs indefinitely here (0 bytes of buffered output). Fault-handler stack:
```
WizardViewModule.onClickedDelete → __deleteWorkflow → InWindowDialog.confirm → InWindowDialog.__run   (blocked)
```
**Root cause:** `test_new_run_saves_then_view_edits_then_delete` calls the delete path, which opens a **modal
in-window confirm dialog** (`InWindowDialog.confirm`) that spins its own event loop waiting for a button click.
Headless, nobody clicks → it blocks forever. A test-harness gap (the test doesn't drive/patch the confirm), not
a product defect. **This is why `pytest tests/` must currently be run per-file with a timeout.**

**Fix (pick one):**
- Monkey-patch `InWindowDialog.confirm` to auto-return **accepted** for this test, **or**
- have the dialog offer a headless/auto-accept hook the test sets, **or**
- drive the confirm button via `QTimer.singleShot` after opening.

Prefer patching `confirm` in the test — smallest, most local. **Effort:** small (test-only). Also add a global
**pytest timeout** (e.g. `pytest-timeout`, `--timeout=120`) so a future modal-in-test fails fast instead of
hanging the suite.

## T3 — `test_pumpkin_wizard_offscreen`: nav-glyph assertion mismatch
**Symptom:**
```
AssertionError: 'Next →' != 'Next ▶'
```
**Root cause:** the wizard's Next-button label glyph changed (`→` vs `▶`) but this assertion still expects the
old glyph. Known since the M1 sweep. Cosmetic/stale-assertion — the button works. **Fix:** update the expected
string to the shipping glyph (or assert on state, not the glyph). **Effort:** trivial (one line).

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
