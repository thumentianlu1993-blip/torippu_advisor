import logging
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.routers import projects

configure_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)


app = FastAPI(title="Travel Planner API", version="0.1.0")

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def require_allowed_origin(request: Request, call_next):
    """Reject every browser mutation unless it has an exact allowed Origin."""
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        parsed_origin = urlsplit(origin) if origin else None
        local_origin = bool(parsed_origin and parsed_origin.hostname in {"localhost", "127.0.0.1"})
        insecure_origin = bool(
            parsed_origin and parsed_origin.scheme != "https" and not local_origin
        )
        if origin not in _cors_origins or origin == "null" or insecure_origin:
            return JSONResponse({"detail": "origin_not_allowed"}, status_code=403)
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            return JSONResponse({"detail": "json_required"}, status_code=415)
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    route = request.scope.get("route")
    route_template = getattr(route, "path", "unmatched")
    logger.info(
        "%s %s - %s - %.3fs",
        request.method,
        route_template,
        response.status_code,
        duration,
    )
    return response


app.include_router(projects.router)


@app.get("/healthz")
async def healthz():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:  # noqa: BLE001
        return JSONResponse(
            {"status": "degraded", "database": "unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.get("/")
def root():
    return {"message": "Travel Planner API"}
