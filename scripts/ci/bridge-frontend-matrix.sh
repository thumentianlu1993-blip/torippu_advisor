#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/../.." && pwd)"
suffix="$$"
network="travel_bridge_smoke_${suffix}"
postgres="travel_bridge_postgres_${suffix}"
bridge="travel_bridge_app_${suffix}"
database="travel_test_bridge_${suffix}"
db_url="postgresql+psycopg://travel:travel@${postgres}:5432/${database}"

cleanup() {
  docker rm -f "${bridge}" "${postgres}" >/dev/null 2>&1 || true
  docker network rm "${network}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "${network}" >/dev/null
docker run -d --name "${postgres}" --network "${network}" \
  -e POSTGRES_USER=travel -e POSTGRES_PASSWORD=travel -e POSTGRES_DB=postgres \
  postgres:16-alpine >/dev/null
for _ in $(seq 1 30); do
  if docker exec "${postgres}" pg_isready -U travel -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "${postgres}" createdb -U travel "${database}"

docker build -t travel-backend:dev "${repo_dir}/backend" >/dev/null
docker build -f "${repo_dir}/backend/Dockerfile.bridge" \
  -t travel-mvp-bridge-v1 "${repo_dir}/backend" >/dev/null
docker run --rm --network "${network}" -e DATABASE_URL="${db_url}" \
  travel-backend:dev alembic upgrade 1c4ac6a7d61c >/dev/null
docker exec "${postgres}" psql -U travel -d "${database}" -v ON_ERROR_STOP=1 -c \
  "INSERT INTO projects (token,destination,duration_days,departure,status,votes_revealed,created_at,updated_at) VALUES ('11111111-1111-1111-1111-111111111111','Legacy',2,'A','draft',0,now(),now()); INSERT INTO candidates (project_id,name,category,tier,source,created_at,updated_at) VALUES (1,'Legacy Spot','cultural','optional','manual',now(),now());" >/dev/null
docker run -d --name "${bridge}" --network "${network}" -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL="${db_url}" travel-mvp-bridge-v1 >/dev/null
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/healthz >/dev/null

run_frontend_smoke() {
  (cd "${repo_dir}/frontend" && BRIDGE_SMOKE=1 \
    npx playwright test e2e/bridge-readonly.spec.ts --project=chromium)
}

run_frontend_smoke
docker run --rm --network "${network}" -e DATABASE_URL="${db_url}" \
  travel-backend:dev alembic upgrade head >/dev/null
run_frontend_smoke
