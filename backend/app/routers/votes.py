import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import cast_vote, get_candidate, get_project
from app.database import get_db
from app.schemas import VoteCreate, VoteRead

router = APIRouter(prefix="/api/candidates/{candidate_id}/votes", tags=["votes"])


def _session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("x-session-id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=31536000,
            httponly=True,
            samesite="lax",
        )
    return session_id


@router.post("", response_model=VoteRead, status_code=status.HTTP_201_CREATED)
async def create_vote(
    candidate_id: int,
    data: VoteCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Ensure project exists (light validation).
    project = await get_project(db, candidate.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    session_id = _session_id(request, response)
    vote = await cast_vote(db, candidate_id, session_id, data)
    await db.commit()
    return vote
