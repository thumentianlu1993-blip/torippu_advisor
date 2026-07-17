import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.routers import candidates, projects, votes

configure_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)


app = FastAPI(title="Travel Planner API", version="0.1.0")

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "%s %s - %s - %.3fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


app.include_router(projects.router)
app.include_router(candidates.router)
app.include_router(votes.router)


@app.get("/healthz")
async def healthz():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"status": "error", "database": str(exc)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.get("/")
def root():
    return {"message": "Travel Planner API"}
