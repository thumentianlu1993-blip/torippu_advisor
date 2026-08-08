#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/../.." && pwd)"
python3 - "${repo_dir}" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
digest = hashlib.sha256()
files = [root / "backend/Dockerfile.bridge", root / "backend/requirements.bridge.txt"]
files.extend(sorted((root / "backend/app").rglob("*.py")))
files.extend(sorted((root / "backend/alembic").rglob("*.py")))
for path in files:
    digest.update(str(path.relative_to(root)).encode())
    digest.update(b"\0")
    digest.update(path.read_bytes())
expected = (root / "backend/bridge-artifact.sha256").read_text().strip()
assert digest.hexdigest() == expected, "bridge artifact hash drifted"
PY
docker build -f "${repo_dir}/backend/Dockerfile.bridge" -t travel-mvp-bridge-v1 "${repo_dir}/backend"
docker run --rm --network none \
  -e DATABASE_URL=postgresql+psycopg://ignored:ignored@127.0.0.1:9/ignored \
  travel-mvp-bridge-v1 python -c \
  'from app.bridge_app import app; from app.bridge_contract import fail_closed; assert app.title.endswith("Bridge");
try: fail_closed("creator")
except PermissionError: pass
else: raise AssertionError("bridge creator write did not fail closed")'
docker image inspect travel-mvp-bridge-v1 --format 'bridge_image_id={{.Id}}'
