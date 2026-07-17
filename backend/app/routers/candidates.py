from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    create_candidate,
    delete_candidate,
    get_candidate,
    get_project,
    get_vote_counts,
    list_candidates,
    update_candidate,
)
from app.database import get_db
from app.schemas import CandidateCreate, CandidateRead, CandidateUpdate

router = APIRouter(prefix="/api/projects/{project_id}/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateRead])
async def read_candidates(
    project_id: int,
    category: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    area: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidates = await list_candidates(db, project_id, category, tier, area, search)

    result = []
    for candidate in candidates:
        counts = await get_vote_counts(db, candidate.id)
        result.append(CandidateRead.model_validate({**candidate.__dict__, **counts}))
    return result


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def add_candidate(
    project_id: int, data: CandidateCreate, db: AsyncSession = Depends(get_db)
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidate = await create_candidate(db, project_id, data)
    await db.commit()
    counts = await get_vote_counts(db, candidate.id)
    return CandidateRead.model_validate({**candidate.__dict__, **counts})


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def patch_candidate(
    project_id: int,
    candidate_id: int,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidate = await get_candidate(db, candidate_id)
    if not candidate or candidate.project_id != project_id:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = await update_candidate(db, candidate, data)
    await db.commit()
    counts = await get_vote_counts(db, candidate.id)
    return CandidateRead.model_validate({**candidate.__dict__, **counts})


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_candidate(
    project_id: int, candidate_id: int, db: AsyncSession = Depends(get_db)
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    candidate = await get_candidate(db, candidate_id)
    if not candidate or candidate.project_id != project_id:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await delete_candidate(db, candidate)
    await db.commit()
    return None
