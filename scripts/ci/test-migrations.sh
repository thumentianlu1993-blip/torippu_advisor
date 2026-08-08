#!/usr/bin/env bash
set -euo pipefail

if [[ "${TRAVEL_DISPOSABLE_DB:-}" != "1" ]]; then
  echo "refusing migration test without TRAVEL_DISPOSABLE_DB=1" >&2
  exit 2
fi
if [[ -z "${TRAVEL_TEST_ADMIN_URL:-}" ]]; then
  echo "TRAVEL_TEST_ADMIN_URL is required; inherited DATABASE_URL is ignored" >&2
  exit 2
fi

# The runner creates TRAVEL_TEST_DATABASE_URL with a random travel_test_ name,
# then performs: alembic upgrade head; alembic downgrade base; alembic upgrade head.
cd "$(dirname "$0")/../../backend"
python scripts/disposable_migration_runner.py
