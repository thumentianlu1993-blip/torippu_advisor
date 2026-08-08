from pathlib import Path

from app.main import app
from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "frontend"


def route_paths() -> set[str]:
    paths: set[str] = set()

    def collect(routes) -> None:
        for route in routes:
            path = getattr(route, "path", "")
            if path.startswith("/api/"):
                paths.add(path)
            included = getattr(route, "original_router", None)
            if included is not None:
                collect(included.routes)

    collect(app.routes)
    return paths


def table(name: str):
    return Base.metadata.tables.get(name)


def source(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""
