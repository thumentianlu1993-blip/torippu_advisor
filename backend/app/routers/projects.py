from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.crud import (
    create_collection_run,
    create_project,
    get_or_create_report,
    get_project,
    get_project_by_token,
    get_project_status,
)
from app.database import AsyncSessionLocal, get_db
from app.models import ProjectStatus, Report
from app.schemas import ProjectCreate, ProjectRead, ProjectStatusRead

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
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
    from app.crud import list_candidates

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


@router.post("/{project_id}/recollect", response_model=ProjectStatusRead)
async def recollect_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus.collecting
    run = await create_collection_run(db, project_id)
    await db.commit()

    celery_app.send_task("app.tasks.collection.run_collection", args=[project.id, run.id])

    status_data = await get_project_status(db, project_id)
    return ProjectStatusRead(**status_data)
