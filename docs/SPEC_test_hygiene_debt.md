# SPEC — Test-suite hygiene debt (pre-existing failures)

Status: **BACKLOG — not blocking any feature.** Catalogues the tests under `spectracsPy/tests/` that do **not**
pass on `main`, each with its root cause and the fix, so they are tracked rather than rediscovered every run.
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

## Not in scope
Product behaviour — all three are test-side (stale fixture, un-driven modal, stale assertion). No application code
change is implied. Fixing them is worthwhile hygiene (a green, non-hanging `pytest tests/`) but gates nothing.
</content>
