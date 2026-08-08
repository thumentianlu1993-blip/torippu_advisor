"""Read-only rollback bridge for pre-expand and expand database schemas."""

import hashlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text

from app.database import AsyncSessionLocal

app = FastAPI(title="Travel MVP Read-Only Bridge", version="bridge-v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def fail_closed_writes(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse({"detail": "bridge_write_disabled"}, status_code=503)
    return await call_next(request)


async def _has_column(session, table_name: str, column_name: str) -> bool:
    return bool(
        await session.scalar(
            text(
                """SELECT 1 FROM information_schema.columns
                WHERE table_schema=current_schema() AND table_name=:table
                AND column_name=:column"""
            ),
            {"table": table_name, "column": column_name},
        )
    )


async def _project_row(session, share_token: str):
    if await _has_column(session, "projects", "share_token_hash"):
        return (
            (
                await session.execute(
                    text(
                        """SELECT id,destination,duration_days,travel_time,departure,
                    traveler_structure,preferences,budget_level,constraints,status,
                    votes_revealed,created_at,updated_at FROM projects
                    WHERE share_token_hash=:token_hash AND deleted_at IS NULL"""
                    ),
                    {"token_hash": hashlib.sha256(share_token.encode()).hexdigest()},
                )
            )
            .mappings()
            .first()
        )
    return (
        (
            await session.execute(
                text(
                    """SELECT id,destination,duration_days,travel_time,departure,
                traveler_structure,preferences,budget_level,constraints,status,
                votes_revealed,created_at,updated_at FROM projects
                WHERE token::text=:share_token"""
                ),
                {"share_token": share_token},
            )
        )
        .mappings()
        .first()
    )


@app.get("/api/projects/by-token/{share_token}")
async def read_project(share_token: str):
    async with AsyncSessionLocal() as session:
        row = await _project_row(session, share_token)
        if not row:
            return JSONResponse({"detail": "not_found"}, status_code=404)
        return {key: value for key, value in row.items() if key != "id"}


@app.get("/api/projects/by-token/{share_token}/report")
async def read_report(share_token: str):
    async with AsyncSessionLocal() as session:
        project = await _project_row(session, share_token)
        if not project:
            return JSONResponse({"detail": "not_found"}, status_code=404)
        report = (
            (
                await session.execute(
                    text(
                        """SELECT status,progress,content,updated_at FROM reports
                    WHERE project_id=:project_id"""
                    ),
                    {"project_id": project["id"]},
                )
            )
            .mappings()
            .first()
        )
        if not report:
            return {
                "status": "pending",
                "progress": 0,
                "content": {},
                "updated_at": project["updated_at"],
            }
        return dict(report)


@app.get("/api/projects/by-token/{share_token}/status")
async def read_status(share_token: str):
    async with AsyncSessionLocal() as session:
        project = await _project_row(session, share_token)
        if not project:
            return JSONResponse({"detail": "not_found"}, status_code=404)
        report = (
            (
                await session.execute(
                    text("SELECT status,progress,updated_at FROM reports WHERE project_id=:id"),
                    {"id": project["id"]},
                )
            )
            .mappings()
            .first()
        )
        run = (
            (
                await session.execute(
                    text(
                        """SELECT status,source_statuses,
                        COALESCE(completed_at,started_at,created_at) AS updated_at
                        FROM collection_runs
                        WHERE project_id=:id ORDER BY created_at DESC LIMIT 1"""
                    ),
                    {"id": project["id"]},
                )
            )
            .mappings()
            .first()
        )
        run_status = run["status"] if run else None
        coverage = "complete" if run_status == "success" else "partial" if run else "stale"
        return {
            "status": project["status"],
            "report_status": report["status"] if report else None,
            "report_progress": report["progress"] if report else 0,
            "collection_status": run_status,
            "updated_at": (report or project)["updated_at"],
            "coverage": coverage,
            "missing_categories": [] if coverage == "complete" else ["部分地点来源"],
        }


@app.get("/api/projects/by-token/{share_token}/candidates")
async def read_candidates(share_token: str):
    async with AsyncSessionLocal() as session:
        project = await _project_row(session, share_token)
        if not project:
            return JSONResponse({"detail": "not_found"}, status_code=404)
        expanded = await _has_column(session, "candidates", "version")
        enriched = await _has_column(session, "candidates", "review_snippets")
        extra = (
            ",version,notes,active" if expanded else ",1 AS version,NULL AS notes,true AS active"
        )
        review_columns = (
            ",chinese_focus_summary,pros,cons,review_snippets"
            if enriched
            else ",NULL AS chinese_focus_summary,NULL AS pros,NULL AS cons,NULL AS review_snippets"
        )
        rows = (
            (
                await session.execute(
                    text(
                        f"""SELECT id,name,category,subcategory,tier,area,lat,lng,rating,
                        review_count,price_level,price_range,opening_hours,source,source_url,
                        summary,photos {review_columns} {extra}
                        FROM candidates WHERE project_id=:id
                        {"AND active=true" if expanded else ""} ORDER BY id"""
                    ),
                    {"id": project["id"]},
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                **dict(row),
                "user_vote": None,
                "like_count": None,
                "dislike_count": None,
                "neutral_count": None,
            }
            for row in rows
        ]


@app.get("/api/projects/by-token/{share_token}/creator-check")
async def creator_check(share_token: str):
    async with AsyncSessionLocal() as session:
        if not await _project_row(session, share_token):
            return JSONResponse({"detail": "not_found"}, status_code=404)
    return {"creator": False, "recovery_required": False, "bridge_read_only": True}


@app.get("/api/projects/by-token/{share_token}/report/stream")
async def report_stream(share_token: str):
    response = await read_report(share_token)
    if isinstance(response, JSONResponse):
        return response

    async def event():
        import json

        payload = {"status": response["status"], "progress": response["progress"]}
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event(), media_type="text/event-stream")


@app.get("/api/projects/by-token/{share_token}/export/google-maps")
async def public_export(share_token: str):
    candidates = await read_candidates(share_token)
    if isinstance(candidates, JSONResponse):
        return candidates
    return {"points": candidates, "count": len(candidates)}


@app.get("/healthz")
async def healthz():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)
    return {"status": "ok", "database": "ok"}
