from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import cast_vote, get_candidate, get_project
from app.database import get_db
from app.schemas import VoteCreate, VoteRead

router = APIRouter(prefix="/api/candidates/{candidate_id}/votes", tags=["votes"])


def _session_id(request: Request) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("x-session-id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session identifier")
    return session_id


@router.post("", response_model=VoteRead, status_code=status.HTTP_201_CREATED)
async def create_vote(
    candidate_id: int,
    data: VoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Ensure project exists (light validation).
    project = await get_project(db, candidate.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session_id = _session_id(request)
    vote = await cast_vote(db, candidate_id, session_id, data)
    await db.commit()
    return vote
