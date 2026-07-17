from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_creator
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


def _candidate_with_counts(candidate, counts: dict) -> CandidateRead:
    return CandidateRead.model_validate(candidate).model_copy(update=counts)


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

    try:
        candidates = await list_candidates(db, project_id, category, tier, area, search)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    result = []
    for candidate in candidates:
        counts = await get_vote_counts(db, candidate.id)
        result.append(_candidate_with_counts(candidate, counts))
    return result


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def add_candidate(
    project_id: int,
    data: CandidateCreate,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_creator(project, x_creator_token)

    candidate = await create_candidate(db, project_id, data)
    await db.commit()
    counts = await get_vote_counts(db, candidate.id)
    return _candidate_with_counts(candidate, counts)


@router.patch("/{candidate_id}", response_model=CandidateRead)
async def patch_candidate(
    project_id: int,
    candidate_id: int,
    data: CandidateUpdate,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_creator(project, x_creator_token)

    candidate = await get_candidate(db, candidate_id)
    if not candidate or candidate.project_id != project_id:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = await update_candidate(db, candidate, data)
    await db.commit()
    counts = await get_vote_counts(db, candidate.id)
    return _candidate_with_counts(candidate, counts)


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_candidate(
    project_id: int,
    candidate_id: int,
    x_creator_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_creator(project, x_creator_token)

    candidate = await get_candidate(db, candidate_id)
    if not candidate or candidate.project_id != project_id:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await delete_candidate(db, candidate)
    await db.commit()
    return None
