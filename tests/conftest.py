"""Shared pytest fixtures for the Spectracs test suite.

Per-test hang watchdog (SPEC_test_hygiene_debt.md T2): a modal that spins its own nested Qt event loop with
nobody to click it (e.g. InWindowDialog.confirm headless) blocks forever and silently stalls the WHOLE suite.
This autouse fixture arms a faulthandler timer around every test: if any single test overruns the budget, it
dumps ALL thread stacks (naming the offending test) and aborts — so a future modal-in-test fails FAST with a
traceback instead of hanging. Dependency-free on purpose (no pytest-timeout): the suite must run in any
environment without an extra pip install, and an unknown --timeout option would itself break the run.

Budget is generous (the slowest real Qt test is ~7s) so it never trips a legitimately slow test.
"""
import faulthandler

import pytest

_PER_TEST_TIMEOUT_SECONDS = 120


@pytest.fixture(autouse=True)
def _hangWatchdog():
    faulthandler.dump_traceback_later(_PER_TEST_TIMEOUT_SECONDS, exit=True)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()
