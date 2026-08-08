#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/../.." && pwd)"
project_name="travel_compose_smoke"
response_file="$(mktemp)"

cleanup() {
  rm -f "${response_file}"
  docker compose -p "${project_name}" -f "${repo_dir}/docker-compose.test.yml" \
    --profile app down -v --remove-orphans >/dev/null 2>&1 || true
}

failure_logs() {
  status=$?
  if [ "${status}" -ne 0 ]; then
    docker compose -p "${project_name}" -f "${repo_dir}/docker-compose.test.yml" \
      --profile app logs --no-color 2>&1 | python3 "${repo_dir}/scripts/ci/sanitize-compose-logs.py" || true
  fi
  cleanup
  exit "${status}"
}
trap failure_logs EXIT

cd "${repo_dir}"
docker compose config >/dev/null
docker compose -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.test.yml --profile app config >/dev/null
docker compose -p "${project_name}" -f docker-compose.test.yml \
  --profile app up -d --build --wait

curl --noproxy '*' --fail --silent --show-error --insecure https://localhost:3443/healthz >/dev/null
curl --noproxy '*' --fail --silent --show-error --insecure https://localhost:3443/ >/dev/null

invalid_status="$(curl --noproxy '*' --silent --output /dev/null --write-out '%{http_code}' --insecure \
  -H 'Origin: https://invalid.example' -H 'Content-Type: application/json' \
  --data '{"destination":"rejected","duration_days":1,"departure":"rejected"}' \
  https://localhost:3443/api/projects)"
test "${invalid_status}" = "403"

valid_status="$(curl --noproxy '*' --silent --output "${response_file}" --write-out '%{http_code}' --insecure \
  -H 'Origin: https://localhost:3443' -H 'Content-Type: application/json' \
  --data '{"destination":"compose smoke","duration_days":1,"departure":"local"}' \
  https://localhost:3443/api/projects)"
test "${valid_status}" = "201"
python3 - "${response_file}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["share_token"]
assert payload["recovery_key"]
PY

reservation_count="$(docker compose -p "${project_name}" -f docker-compose.test.yml \
  exec -T postgres-test psql -U travel -d travel_test_ci -Atqc \
  'SELECT count(*) FROM external_call_reservations')"
test "${reservation_count}" = "0"
docker compose -p "${project_name}" -f docker-compose.test.yml exec -T mock-provider \
  python -c "import urllib.request; assert urllib.request.urlopen('http://localhost:8080/healthz').status == 200"

trap - EXIT
cleanup
