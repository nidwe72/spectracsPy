"""AE.4 — AllEntities completeness guard (SPEC_schema_migrations.md §8).

`AllEntities` must import EVERY mapped entity so both metadatas (DbBaseEntity = app DB, ServerDbBaseEntity =
server DB) are complete when Alembic reads `target_metadata` and when `create_all` runs. Until now the only thing
enforcing that was a docstring — and it silently omitted the 7-table `model.spectral` workflow graph, so Alembic
autogenerate proposed DROPPING those tables (the A3 / F-a3-3 incident). This test makes the invariant self-enforcing.

Strategy — curated-import-then-walk, run in a FRESH subprocess:
  1. Import `AllEntities` FIRST — its curated order builds the relationship graph safely (the workflow parent
     imports its children at the bottom; children never import back up), so no partially-initialised-module cycle.
  2. Snapshot the tables each metadata now DECLARES.
  3. Filesystem-walk the real `-model` source tree (located via `DbBase.__file__`) and import every module —
     forces any entity module AllEntities forgot to register its table; already-loaded modules re-import as no-ops.
  4. Report anything the walk discovered that AllEntities did not declare — those are the forgotten entities.

Why a subprocess: SQLAlchemy metadata is process-global, and pytest COLLECTS (imports) every test module before
running — several import `model.spectral`, which would register the workflow tables and mask an AllEntities omission.
A fresh interpreter measures what `AllEntities` truly declares, uncontaminated by the rest of the suite.

Why a filesystem walk (not `pkgutil.walk_packages`): `sciens.spectracs.model` is a NAMESPACE package spanning both
repos (the app repo has a `model/` dir of Qt-bound signals) — `walk_packages` over that multi-root namespace yields
nothing and would pull Qt. Rooting the walk at `-model`'s `DbBase.__file__` pins discovery to the one tree where every
entity actually lives (verified: no entity class is defined in the app repo), and stays Qt-free.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_all_entities_complete.py -q
"""
import subprocess
import sys
import textwrap
import unittest

# Runs in an isolated interpreter (inherits this process's PYTHONPATH via os.environ). Prints one line
# "MISSING:<comma-separated tables>" — empty tail means AllEntities is complete.
_ORACLE = textwrap.dedent(
    """
    import os, importlib
    import sciens.spectracs.model.databaseEntity.AllEntities  # noqa  -- curated import FIRST (safe order)
    from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity
    import sciens.spectracs.model.databaseEntity.DbBase as _dbBase
    from sciens.spectracs.model.databaseEntity.DbServerBase import ServerDbBaseEntity

    declared = set(DbBaseEntity.metadata.tables) | set(ServerDbBaseEntity.metadata.tables)

    modelDir = os.path.dirname(os.path.dirname(_dbBase.__file__))  # -model .../sciens/spectracs/model
    for root, _dirs, files in os.walk(modelDir):
        for fileName in files:
            if not fileName.endswith(".py") or fileName == "__init__.py":
                continue
            rel = os.path.relpath(os.path.join(root, fileName), modelDir)[:-3]
            moduleName = "sciens.spectracs.model." + rel.replace(os.sep, ".")
            try:
                importlib.import_module(moduleName)
            except Exception:
                pass  # a module that cannot import in isolation cannot be a usable entity; discovery is best-effort

    actual = set(DbBaseEntity.metadata.tables) | set(ServerDbBaseEntity.metadata.tables)
    print("MISSING:" + ",".join(sorted(actual - declared)))
    """
)


class AllEntitiesCompletenessTest(unittest.TestCase):

    def test_all_entities_are_listed(self):
        result = subprocess.run([sys.executable, "-c", _ORACLE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "oracle subprocess failed:\n" + result.stderr)

        lines = [ln for ln in result.stdout.splitlines() if ln.startswith("MISSING:")]
        self.assertTrue(lines, "oracle produced no MISSING line:\n" + result.stdout + result.stderr)
        missing = lines[-1][len("MISSING:"):].strip()

        self.assertEqual(
            missing, "",
            "AllEntities is INCOMPLETE — these mapped tables register only after a full model-tree walk, so their "
            "entity modules are missing from AllEntities.py. Add them (SPEC_schema_migrations.md §8): " + missing,
        )


if __name__ == "__main__":
    unittest.main()
