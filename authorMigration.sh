#!/usr/bin/env bash
# Author a new Alembic migration (SPEC_schema_migrations.md §3.1) — a DEVELOPER action, run only when a model
# changes; never shipped to a user (the app/server apply migrations automatically at boot). Usage:
#     ./authorMigration.sh <app|server> "short message"
# Then REVIEW the generated file under ../spectracsPy-model/alembic/<db>/versions/ and commit it.
set -euo pipefail

DB="${1:-}"; MSG="${2:-}"
if [[ "$DB" != "app" && "$DB" != "server" ]] || [[ -z "$MSG" ]]; then
    echo "usage: ./authorMigration.sh <app|server> \"message\"" >&2
    exit 2
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"
exec "$HERE/venv/bin/python" -m alembic \
    -c "../spectracsPy-model/alembic/$DB/alembic.ini" \
    revision --autogenerate -m "$MSG"
