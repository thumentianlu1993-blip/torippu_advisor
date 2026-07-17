from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_creator
from app.celery_app import celery_app
from app.crud import (
    create_collection_run,
    create_project,
    get_or_create_report,
    get_project,
    get_project_by_token,
    get_project_status,
    list_candidates,
)
from app.database import AsyncSessionLocal, get_db
from app.models import Project, ProjectStatus, Report
from app.schemas import ProjectCreate, ProjectCreated, ProjectRead, ProjectStatusRead

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _get_project_by_token_or_404(db: AsyncSession, token: UUID) -> Project:
    project = await get_project_by_token(db, token)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectCreated, status_code=status.HTTP_201_CREATED)
async def create_new_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = await create_project(db, data)
    await get_or_create_report(db, project.id)
    run = await create_collection_run(db, project.id)
    await db.commit()

    # Trigger collection pipeline asynchronously.
    celery_app.send_task("app.tasks.collection.run_collection", args=[project.id, run.id])

    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/by-token/{token}", response_model=ProjectRead)
async def read_project_by_token(token: UUID, db: AsyncSession = Depends(get_db)):
    project = await get_project_by_token(db, token)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/by-token/{token}/creator-check")
async def creator_check(
    token: UUID,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Validate a creator token without exposing it in any other response."""
    project = await _get_project_by_token_or_404(db, token)
    return {
        "creator": bool(x_creator_token)
        and x_creator_token == str(project.creator_token)
    }


@router.get("/{project_id}/status", response_model=ProjectStatusRead)
async def read_project_status(project_id: int, db: AsyncSession = Depends(get_db)):
    status_data = await get_project_status(db, project_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectStatusRead(**status_data)


@router.get("/{project_id}/report")
async def read_project_report(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(Report).where(Report.project_id == project_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "project_id": project_id,
        "status": report.status.value,
        "progress": report.progress,
        "content": report.content,
        "updated_at": report.updated_at,
    }


@router.get("/{project_id}/report/stream")
async def stream_project_report(project_id: int, db: AsyncSession = Depends(get_db)):
    """SSE stream of report generation progress."""
    import asyncio
    import json

    async def event_generator():
        for _ in range(60):  # 60 iterations x 2s = 2 minutes max
            async with AsyncSessionLocal() as session:  # noqa: F821
                result = await session.execute(
                    select(Report).where(Report.project_id == project_id)
                )
                report = result.scalar_one_or_none()
                if report:
                    data = {
                        "status": report.status.value,
                        "progress": report.progress,
                        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    if report.status.value in ("success", "failed"):
                        break
                else:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{project_id}/export/google-maps")
async def export_google_maps(project_id: int, db: AsyncSession = Depends(get_db)):
    """Export candidate coordinates as a Google Maps-compatible JSON list."""
    from fastapi.responses import JSONResponse

    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidates = await list_candidates(db, project_id)
    points = [
        {
            "name": c.name,
            "lat": c.lat,
            "lng": c.lng,
            "category": c.category.value,
            "tier": c.tier.value,
            "source": c.source,
        }
        for c in candidates
        if c.lat is not None and c.lng is not None
    ]
    return JSONResponse(
        content={
            "project_id": project_id,
            "destination": project.destination,
            "points": points,
            "count": len(points),
        }
    )


# Token-based endpoints avoid exposing sequential integer project IDs to clients.


@router.get("/by-token/{token}/status", response_model=ProjectStatusRead)
async def read_project_status_by_token(token: UUID, db: AsyncSession = Depends(get_db)):
    project = await _get_project_by_token_or_404(db, token)
    status_data = await get_project_status(db, project.id)
    return ProjectStatusRead(**status_data)


@router.get("/by-token/{token}/report")
async def read_project_report_by_token(token: UUID, db: AsyncSession = Depends(get_db)):
    project = await _get_project_by_token_or_404(db, token)
    result = await db.execute(select(Report).where(Report.project_id == project.id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "project_id": project.id,
        "status": report.status.value,
        "progress": report.progress,
        "content": report.content,
        "updated_at": report.updated_at,
    }


@router.get("/by-token/{token}/candidates")
async def read_candidates_by_token(
    token: UUID,
    category: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    area: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    from app.crud import get_vote_counts
    from app.routers.candidates import _candidate_with_counts

    project = await _get_project_by_token_or_404(db, token)
    try:
        candidates = await list_candidates(db, project.id, category, tier, area, search)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    result = []
    for candidate in candidates:
        counts = await get_vote_counts(db, candidate.id)
        result.append(_candidate_with_counts(candidate, counts))
    return result


@router.get("/by-token/{token}/export/google-maps")
async def export_google_maps_by_token(token: UUID, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import JSONResponse

    project = await _get_project_by_token_or_404(db, token)
    candidates = await list_candidates(db, project.id)
    points = [
        {
            "name": c.name,
            "lat": c.lat,
            "lng": c.lng,
            "category": c.category.value,
            "tier": c.tier.value,
            "source": c.source,
        }
        for c in candidates
        if c.lat is not None and c.lng is not None
    ]
    return JSONResponse(
        content={
            "destination": project.destination,
            "points": points,
            "count": len(points),
        }
    )


@router.post("/by-token/{token}/recollect", response_model=ProjectStatusRead)
async def recollect_project_by_token(
    token: UUID,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_by_token_or_404(db, token)
    require_creator(project, x_creator_token)
    project.status = ProjectStatus.collecting
    run = await create_collection_run(db, project.id)
    await db.commit()

    celery_app.send_task("app.tasks.collection.run_collection", args=[project.id, run.id])

    status_data = await get_project_status(db, project.id)
    return ProjectStatusRead(**status_data)


@router.post("/{project_id}/recollect", response_model=ProjectStatusRead)
async def recollect_project(
    project_id: int,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_creator(project, x_creator_token)

    project.status = ProjectStatus.collecting
    run = await create_collection_run(db, project_id)
    await db.commit()

    celery_app.send_task("app.tasks.collection.run_collection", args=[project.id, run.id])

    status_data = await get_project_status(db, project_id)
    return ProjectStatusRead(**status_data)
