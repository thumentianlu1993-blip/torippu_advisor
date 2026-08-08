"""Share-token-scoped browser API.

Internal integer project ids never form part of a browser route or response.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    CREATOR_COOKIE,
    VOTER_COOKIE,
    new_secret,
    require_creator,
    secret_hash,
    secret_matches,
)
from app.crud import (
    create_collection_run,
    create_project,
    get_or_create_report,
    get_project_by_token,
    get_project_status,
    get_vote_counts,
    list_candidates,
)
from app.database import AsyncSessionLocal, get_db
from app.models import (
    Candidate,
    CandidateFieldChange,
    CandidateFieldOverride,
    CollectionRun,
    CollectionStatus,
    ExternalCallReservation,
    MergeProposal,
    Project,
    ProjectStatus,
    Report,
    TaskOutbox,
    Vote,
    VoteType,
)
from app.schemas import (
    CandidateCreate,
    CandidateRead,
    CandidateUpdate,
    ProjectCreate,
    ProjectCreated,
    ProjectRead,
    ProjectStatusRead,
    VoteCreate,
    VoteRead,
)
from app.services.candidate_merge import decide_proposal
from app.services.rate_limits import (
    enforce_project_create_limit,
    enforce_recollect_limit,
    enforce_recovery_limit,
    enforce_vote_limit,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])
COOKIE_MAX_AGE = 15552000


def _cookie_path(share_token: str) -> str:
    return f"/api/projects/by-token/{share_token}"


def _set_cookie(response: Response, name: str, value: str, share_token: str) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=15552000,
        path=_cookie_path(share_token),
        httponly=True,
        secure=True,
        samesite="lax",
    )


async def _project(db: AsyncSession, share_token: str, *, include_deleted: bool = False) -> Project:
    if include_deleted:
        result = await db.execute(
            select(Project).where(Project.share_token_hash == secret_hash(share_token))
        )
        project = result.scalar_one_or_none()
    else:
        project = await get_project_by_token(db, share_token)
    if not project:
        raise HTTPException(status_code=404, detail="not_found")
    return project


async def _lock_project(db: AsyncSession, project: Project) -> Project:
    locked = await db.scalar(select(Project).where(Project.id == project.id).with_for_update())
    if not locked:
        raise HTTPException(status_code=404, detail="not_found")
    return locked


async def _bump_candidate_version_and_queue_report(db: AsyncSession, project: Project) -> None:
    """Atomically invalidate the report and persist one rebuild intent per version."""
    project.candidate_data_version += 1
    latest_run_id = await db.scalar(
        select(CollectionRun.id)
        .where(CollectionRun.project_id == project.id)
        .order_by(CollectionRun.created_at.desc())
        .limit(1)
    )
    version = project.candidate_data_version
    await db.execute(
        pg_insert(TaskOutbox)
        .values(
            project_id=project.id,
            run_id=latest_run_id,
            task_name="app.tasks.report.generate_report",
            dedupe_key=f"report:{project.id}:{version}",
            payload={"args": [project.id, version]},
        )
        .on_conflict_do_nothing(index_elements=[TaskOutbox.dedupe_key])
    )


def _project_read(project: Project) -> dict:
    return {name: getattr(project, name) for name in ProjectRead.model_fields}


async def _candidate_read(
    db: AsyncSession,
    candidate: Candidate,
    *,
    counts: dict | None = None,
    user_vote: str | None = None,
) -> CandidateRead:
    data = CandidateRead.model_validate(candidate)
    updates = {"user_vote": user_vote}
    overrides = (
        await db.execute(
            select(CandidateFieldOverride).where(
                CandidateFieldOverride.candidate_id == candidate.id
            )
        )
    ).scalars()
    updates.update({item.field_name: item.value for item in overrides})
    if counts is not None:
        updates.update(counts)
    return data.model_copy(update=updates)


@router.post("", response_model=ProjectCreated, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    data: ProjectCreate, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    await enforce_project_create_limit(request)
    project = await create_project(db, data)
    project.creator_credential_expires_at = datetime.now(timezone.utc) + timedelta(days=180)
    await get_or_create_report(db, project.id)
    run = await create_collection_run(db, project.id)
    db.add(
        TaskOutbox(
            project_id=project.id,
            run_id=run.id,
            task_name="app.tasks.collection.run_collection",
            dedupe_key=f"collection:{run.id}",
            payload={"args": [project.id, run.id]},
        )
    )
    await db.commit()
    share_token = project._share_token_plain
    _set_cookie(response, CREATOR_COOKIE, project._creator_credential_plain, share_token)
    return {
        **_project_read(project),
        "share_token": share_token,
        "recovery_key": project._recovery_key_plain,
    }


@router.get("/by-token/{share_token}", response_model=ProjectRead)
async def read_project_by_token(share_token: str, db: AsyncSession = Depends(get_db)):
    return _project_read(await _project(db, share_token))


@router.get("/by-token/{share_token}/creator-check")
async def creator_check(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    try:
        require_creator(project, request)
    except HTTPException:
        return {"creator": False, "recovery_required": bool(project.recovery_key_hash)}
    return {"creator": True, "recovery_required": False}


@router.get("/by-token/{share_token}/status", response_model=ProjectStatusRead)
async def read_project_status_by_token(share_token: str, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    return ProjectStatusRead(**await get_project_status(db, project.id))


@router.get("/by-token/{share_token}/report")
async def read_project_report_by_token(share_token: str, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    result = await db.execute(select(Report).where(Report.project_id == project.id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="not_found")
    report_status = report.status.value
    if (
        report.status == CollectionStatus.success
        and report.generated_from_version != project.candidate_data_version
    ):
        report_status = "stale"
    return {
        "status": report_status,
        "progress": report.progress,
        "content": report.content,
        "updated_at": report.updated_at,
    }


@router.get("/by-token/{share_token}/report/stream")
async def stream_project_report(share_token: str, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    expected_version = project.share_token_version

    async def events():
        for _ in range(60):
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Project, Report)
                    .join(Report, Report.project_id == Project.id)
                    .where(Project.id == project.id)
                )
                row = result.first()
                if (
                    not row
                    or row.Project.deleted_at
                    or row.Project.share_token_version != expected_version
                ):
                    yield "event: revoked\ndata: {}\n\n"
                    return
                report_status = row.Report.status.value
                if (
                    row.Report.status == CollectionStatus.success
                    and row.Report.generated_from_version != row.Project.candidate_data_version
                ):
                    report_status = "stale"
                payload = {
                    "status": report_status,
                    "progress": row.Report.progress,
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if row.Report.status in {CollectionStatus.success, CollectionStatus.failed}:
                    return
            await asyncio.sleep(2)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/by-token/{share_token}/candidates", response_model=list[CandidateRead])
async def read_candidates_by_token(
    share_token: str,
    request: Request,
    category: str | None = Query(None),
    tier: str | None = Query(None),
    area: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    project = await _project(db, share_token)
    candidates = await list_candidates(db, project.id, category, tier, area, search)
    voter = request.cookies.get(VOTER_COOKIE)
    voter_hash = secret_hash(f"{project.id}:{voter}") if voter else None
    output = []
    for candidate in candidates:
        own = None
        if voter_hash:
            result = await db.execute(
                select(Vote).where(Vote.candidate_id == candidate.id, Vote.voter_hash == voter_hash)
            )
            vote = result.scalar_one_or_none()
            own = vote.vote_type.value if vote else None
        counts = await get_vote_counts(db, candidate.id) if project.votes_revealed else None
        output.append(await _candidate_read(db, candidate, counts=counts, user_vote=own))
    return output


@router.post(
    "/by-token/{share_token}/candidates/{candidate_id}/votes",
    response_model=VoteRead,
    status_code=201,
)
async def create_vote(
    share_token: str,
    candidate_id: int,
    data: VoteCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    project = await _project(db, share_token)
    candidate = await db.get(Candidate, candidate_id)
    if not candidate or candidate.project_id != project.id:
        raise HTTPException(status_code=404, detail="not_found")
    voter = request.cookies.get(VOTER_COOKIE) or new_secret()
    voter_hash = secret_hash(f"{project.id}:{voter}")
    await enforce_vote_limit(request, secret_hash(share_token)[:16], f"{voter_hash}:{candidate_id}")
    statement = (
        pg_insert(Vote)
        .values(
            candidate_id=candidate.id,
            voter_hash=voter_hash,
            vote_type=VoteType(data.vote_type),
        )
        .on_conflict_do_update(
            index_elements=[Vote.candidate_id, Vote.voter_hash],
            set_={"vote_type": VoteType(data.vote_type), "updated_at": func.now()},
        )
        .returning(Vote)
    )
    vote = (await db.execute(statement)).scalar_one()
    await db.commit()
    _set_cookie(response, VOTER_COOKIE, voter, share_token)
    return vote


def _point(candidate, counts: dict | None) -> dict:
    category = (
        candidate.category.value if hasattr(candidate.category, "value") else candidate.category
    )
    tier = candidate.tier.value if hasattr(candidate.tier, "value") else candidate.tier
    point = {
        "name": candidate.name,
        "lat": candidate.lat,
        "lng": candidate.lng,
        "category": category,
        "tier": tier,
        "source": candidate.source,
    }
    if counts is not None:
        point["votes"] = counts
    return point


async def _export(project: Project, db: AsyncSession, *, creator: bool) -> JSONResponse:
    points = []
    for candidate in await list_candidates(db, project.id):
        if candidate.lat is not None and candidate.lng is not None:
            counts = (
                await get_vote_counts(db, candidate.id)
                if creator or project.votes_revealed
                else None
            )
            effective = await _candidate_read(db, candidate, counts=counts)
            points.append(_point(effective, counts))
    return JSONResponse(
        {
            "destination": project.destination,
            "votes_revealed": bool(project.votes_revealed),
            "points": points,
            "count": len(points),
        }
    )


@router.get("/by-token/{share_token}/export/google-maps")
async def export_google_maps(share_token: str, db: AsyncSession = Depends(get_db)):
    return await _export(await _project(db, share_token), db, creator=False)


@router.get("/by-token/{share_token}/creator/export/google-maps")
async def creator_export_google_maps(
    share_token: str, request: Request, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    require_creator(project, request)
    return await _export(project, db, creator=True)


@router.post("/by-token/{share_token}/recollect", response_model=ProjectStatusRead)
async def recollect_project(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    result = await db.execute(
        select(CollectionRun)
        .where(
            CollectionRun.project_id == project.id,
            CollectionRun.status.in_(
                [CollectionStatus.pending, CollectionStatus.running, CollectionStatus.generating]
            ),
        )
        .with_for_update()
    )
    run = result.scalar_one_or_none()
    if run:
        return ProjectStatusRead(**await get_project_status(db, project.id))
    await enforce_recollect_limit(request, secret_hash(share_token)[:16])
    lifetime = (
        await db.execute(
            select(
                func.coalesce(func.sum(ExternalCallReservation.request_units), 0),
                func.coalesce(func.sum(ExternalCallReservation.estimated_cost_usd), 0),
            ).where(ExternalCallReservation.project_id == project.id)
        )
    ).one()
    if int(lifetime[0]) >= 500 or float(lifetime[1]) >= 2:
        raise HTTPException(status_code=409, detail="lifetime_budget_exhausted")
    run = await create_collection_run(db, project.id)
    db.add(
        TaskOutbox(
            project_id=project.id,
            run_id=run.id,
            task_name="app.tasks.collection.run_collection",
            dedupe_key=f"collection:{run.id}",
            payload={"args": [project.id, run.id]},
        )
    )
    project.status = ProjectStatus.collecting
    await db.commit()
    return ProjectStatusRead(**await get_project_status(db, project.id))


@router.patch("/by-token/{share_token}/creator/votes-visibility")
async def set_votes_visibility(
    share_token: str, data: dict, request: Request, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    project.votes_revealed = int(bool(data.get("revealed")))
    await db.commit()
    return {"votes_revealed": bool(project.votes_revealed)}


@router.get("/by-token/{share_token}/creator/coverage")
async def creator_coverage(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    require_creator(project, request)
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(ExternalCallReservation.request_units), 0),
                func.coalesce(func.sum(ExternalCallReservation.estimated_cost_usd), 0),
            ).where(ExternalCallReservation.project_id == project.id)
        )
    ).one()
    latest = await db.scalar(
        select(CollectionRun)
        .where(CollectionRun.project_id == project.id)
        .order_by(CollectionRun.created_at.desc())
        .limit(1)
    )
    return {
        "request_units": int(totals[0]),
        "request_limit": 500,
        "estimated_cost_usd": float(totals[1]),
        "cost_limit_usd": 2,
        "source_statuses": latest.source_statuses if latest else {},
        "blocked_reason": (
            "lifetime_budget_exhausted" if int(totals[0]) >= 500 or float(totals[1]) >= 2 else None
        ),
    }


@router.post(
    "/by-token/{share_token}/creator/candidates", response_model=CandidateRead, status_code=201
)
async def add_manual_candidate(
    share_token: str, data: CandidateCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    count = await db.scalar(
        select(func.count(Candidate.id)).where(
            Candidate.project_id == project.id, Candidate.active.is_(True)
        )
    )
    if count >= 300:
        raise HTTPException(status_code=409, detail="candidate_capacity_reached")
    candidate = Candidate(
        project_id=project.id,
        name=data.name,
        category=data.category,
        tier=data.tier,
        area=data.area,
        source="manual",
        source_url=data.source_url,
        summary=data.summary,
        notes=data.notes,
        origin="manual",
    )
    db.add(candidate)
    await _bump_candidate_version_and_queue_report(db, project)
    await db.commit()
    await db.refresh(candidate)
    return await _candidate_read(db, candidate)


@router.patch(
    "/by-token/{share_token}/creator/candidates/{candidate_id}", response_model=CandidateRead
)
async def update_manual_candidate(
    share_token: str,
    candidate_id: int,
    data: CandidateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    candidate = await db.get(Candidate, candidate_id)
    if not candidate or candidate.project_id != project.id:
        raise HTTPException(status_code=404, detail="not_found")
    if data.version is not None and data.version != candidate.version:
        raise HTTPException(status_code=409, detail="candidate_version_conflict")
    editable = {"name", "category", "area", "source_url", "notes", "tier", "summary"}
    changes = data.model_dump(exclude_unset=True)
    changes.pop("version", None)
    for field_name, value in changes.items():
        if field_name not in editable:
            continue
        existing = await db.scalar(
            select(CandidateFieldOverride).where(
                CandidateFieldOverride.candidate_id == candidate.id,
                CandidateFieldOverride.field_name == field_name,
            )
        )
        base_value = getattr(candidate, field_name)
        if hasattr(base_value, "value"):
            base_value = base_value.value
        old_value = existing.value if existing else base_value
        next_version = candidate.version + 1
        if value is None:
            if existing:
                await db.delete(existing)
            new_value = base_value
        elif existing:
            existing.value = value
            existing.version = next_version
            new_value = value
        else:
            db.add(
                CandidateFieldOverride(
                    candidate_id=candidate.id,
                    field_name=field_name,
                    value=value,
                    version=next_version,
                )
            )
            new_value = value
        db.add(
            CandidateFieldChange(
                candidate_id=candidate.id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                actor_role="creator",
                version=next_version,
            )
        )
        candidate.version = next_version
    await _bump_candidate_version_and_queue_report(db, project)
    await db.commit()
    await db.refresh(candidate)
    return await _candidate_read(db, candidate)


@router.delete("/by-token/{share_token}/creator/candidates/{candidate_id}", status_code=204)
async def remove_manual_candidate(
    share_token: str, candidate_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    candidate = await db.get(Candidate, candidate_id)
    if not candidate or candidate.project_id != project.id:
        raise HTTPException(status_code=404, detail="not_found")
    candidate.active = False
    await _bump_candidate_version_and_queue_report(db, project)
    await db.commit()


@router.get("/by-token/{share_token}/creator/candidates/{candidate_id}/history")
async def candidate_history(
    share_token: str, candidate_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    require_creator(project, request)
    candidate = await db.get(Candidate, candidate_id)
    if not candidate or candidate.project_id != project.id:
        raise HTTPException(status_code=404, detail="not_found")
    changes = list(
        (
            await db.execute(
                select(CandidateFieldChange)
                .where(CandidateFieldChange.candidate_id == candidate.id)
                .order_by(CandidateFieldChange.created_at.desc())
                .limit(100)
            )
        ).scalars()
    )
    return [
        {
            "id": item.id,
            "field_name": item.field_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "restored_from_id": item.restored_from_id,
            "version": item.version,
            "created_at": item.created_at,
        }
        for item in changes
    ]


@router.post("/by-token/{share_token}/creator/candidates/{candidate_id}/restore")
async def restore_candidate_field(
    share_token: str,
    candidate_id: int,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    candidate = await db.get(Candidate, candidate_id)
    if not candidate or candidate.project_id != project.id:
        raise HTTPException(status_code=404, detail="not_found")
    if data.get("version") != candidate.version:
        raise HTTPException(status_code=409, detail="candidate_version_conflict")
    target = await db.get(CandidateFieldChange, data.get("change_id"))
    if not target or target.candidate_id != candidate.id:
        raise HTTPException(status_code=404, detail="change_not_found")
    existing = await db.scalar(
        select(CandidateFieldOverride).where(
            CandidateFieldOverride.candidate_id == candidate.id,
            CandidateFieldOverride.field_name == target.field_name,
        )
    )
    base_value = getattr(candidate, target.field_name)
    if hasattr(base_value, "value"):
        base_value = base_value.value
    current = existing.value if existing else base_value
    desired = target.old_value
    next_version = candidate.version + 1
    if desired == base_value:
        if existing:
            await db.delete(existing)
    elif existing:
        existing.value = desired
        existing.version = next_version
    else:
        db.add(
            CandidateFieldOverride(
                candidate_id=candidate.id,
                field_name=target.field_name,
                value=desired,
                version=next_version,
            )
        )
    db.add(
        CandidateFieldChange(
            candidate_id=candidate.id,
            field_name=target.field_name,
            old_value=current,
            new_value=desired,
            restored_from_id=target.id,
            actor_role="creator",
            version=next_version,
        )
    )
    candidate.version = next_version
    await _bump_candidate_version_and_queue_report(db, project)
    await db.commit()
    return {"status": "restored", "version": next_version}


@router.get("/by-token/{share_token}/creator/merge-proposals")
async def merge_proposals(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    require_creator(project, request)
    proposals = list(
        (
            await db.execute(
                select(MergeProposal).where(
                    MergeProposal.project_id == project.id,
                    MergeProposal.status == "pending",
                )
            )
        ).scalars()
    )
    output = []
    for item in proposals:
        first = await db.get(Candidate, item.candidate_a_id)
        second = await db.get(Candidate, item.candidate_b_id)
        if not first or not second:
            continue
        output.append(
            {
                "id": item.id,
                "name_a": first.name,
                "name_b": second.name,
                "category_a": first.category.value,
                "category_b": second.category.value,
                "area_a": first.area,
                "area_b": second.area,
                "source_url_a": first.source_url,
                "source_url_b": second.source_url,
                "score": item.score,
                "reasons": item.reasons,
            }
        )
    return output


@router.post("/by-token/{share_token}/creator/merge-proposals/{proposal_id}/decision")
async def decide_merge(
    share_token: str,
    proposal_id: int,
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    try:
        proposal = await decide_proposal(db, project.id, proposal_id, str(data.get("decision")))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="proposal_not_found") from exc
    await _bump_candidate_version_and_queue_report(db, project)
    await db.commit()
    return {"status": proposal.status}


@router.post("/by-token/{share_token}/creator/share-rotation")
async def rotate_share(
    share_token: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    replacement = new_secret()
    project.share_token_hash = secret_hash(replacement)
    project.share_token_version += 1
    credential = request.cookies[CREATOR_COOKIE]
    await db.commit()
    response.delete_cookie(CREATOR_COOKIE, path=_cookie_path(share_token))
    _set_cookie(response, CREATOR_COOKIE, credential, replacement)
    return {"share_token": replacement}


@router.post("/by-token/{share_token}/delete", status_code=204)
async def delete_project(share_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    project = await _project(db, share_token)
    project = await _lock_project(db, project)
    require_creator(project, request)
    now = datetime.now(timezone.utc)
    project.deleted_at = now
    project.purge_after = now + timedelta(days=30)
    project.execution_fence_version += 1
    project.share_token_version += 1
    await db.execute(
        update(CollectionRun)
        .where(
            CollectionRun.project_id == project.id,
            CollectionRun.status.in_(
                [CollectionStatus.pending, CollectionStatus.running, CollectionStatus.generating]
            ),
        )
        .values(status=CollectionStatus.cancelled, cancelled_at=now)
    )
    await db.execute(
        update(TaskOutbox)
        .where(TaskOutbox.project_id == project.id, TaskOutbox.dispatched_at.is_(None))
        .values(cancelled_at=now)
    )
    await db.commit()


@router.post("/by-token/{share_token}/recover")
async def recover_project(
    share_token: str,
    data: dict,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await enforce_recovery_limit(request, secret_hash(share_token)[:16])
    project = await _project(db, share_token, include_deleted=True)
    project = await _lock_project(db, project)
    now = datetime.now(timezone.utc)
    deleted_outside_window = bool(
        project.deleted_at and (not project.purge_after or project.purge_after <= now)
    )
    if deleted_outside_window or not secret_matches(
        data.get("recovery_key"), project.recovery_key_hash
    ):
        raise HTTPException(status_code=404, detail="not_found")
    replacement = new_secret() if project.deleted_at else share_token
    credential = new_secret()
    project.share_token_hash = secret_hash(replacement)
    project.creator_credential_hash = secret_hash(credential)
    project.creator_credential_expires_at = now + timedelta(days=180)
    if project.deleted_at:
        project.deleted_at = None
        project.purge_after = None
        project.share_token_version += 1
    project.creator_credential_version += 1
    await db.commit()
    _set_cookie(response, CREATOR_COOKIE, credential, replacement)
    return {"share_token": replacement}
