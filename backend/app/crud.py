from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Candidate,
    CandidateCategory,
    CandidateTier,
    CollectionRun,
    CollectionStatus,
    Project,
    Report,
    Vote,
    VoteType,
)
from app.schemas import CandidateCreate, CandidateUpdate, ProjectCreate, VoteCreate

# Projects


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(
        destination=data.destination,
        duration_days=data.duration_days,
        travel_time=data.travel_time,
        departure=data.departure,
        traveler_structure=data.traveler_structure,
        preferences=data.preferences,
        budget_level=data.budget_level,
        constraints=data.constraints,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def get_project_by_token(db: AsyncSession, token: UUID) -> Project | None:
    result = await db.execute(select(Project).where(Project.token == token))
    return result.scalar_one_or_none()


async def get_project_status(db: AsyncSession, project_id: int) -> dict:
    project = await get_project(db, project_id)
    if not project:
        return None

    result = await db.execute(select(Report).where(Report.project_id == project_id))
    report = result.scalar_one_or_none()

    result = await db.execute(
        select(CollectionRun)
        .where(CollectionRun.project_id == project_id)
        .order_by(CollectionRun.created_at.desc())
        .limit(1)
    )
    latest_run = result.scalar_one_or_none()

    return {
        "project_id": project.id,
        "status": project.status.value,
        "report_status": report.status.value if report else None,
        "report_progress": report.progress if report else 0,
        "collection_status": latest_run.status.value if latest_run else None,
        "updated_at": project.updated_at,
    }


# Candidates


async def list_candidates(
    db: AsyncSession,
    project_id: int,
    category: str | None = None,
    tier: str | None = None,
    area: str | None = None,
    search: str | None = None,
) -> list[Candidate]:
    stmt = select(Candidate).where(Candidate.project_id == project_id)
    if category:
        stmt = stmt.where(Candidate.category == CandidateCategory(category))
    if tier:
        stmt = stmt.where(Candidate.tier == CandidateTier(tier))
    if area:
        stmt = stmt.where(Candidate.area.ilike(f"%{area}%"))
    if search:
        stmt = stmt.where(Candidate.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Candidate.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_candidate(db: AsyncSession, candidate_id: int) -> Candidate | None:
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def create_candidate(db: AsyncSession, project_id: int, data: CandidateCreate) -> Candidate:
    candidate = Candidate(
        project_id=project_id,
        name=data.name,
        category=CandidateCategory(data.category),
        subcategory=data.subcategory,
        tier=CandidateTier(data.tier),
        area=data.area,
        lat=data.lat,
        lng=data.lng,
        rating=data.rating,
        review_count=data.review_count,
        price_level=data.price_level,
        price_range=data.price_range,
        opening_hours=data.opening_hours,
        source=data.source,
        source_url=data.source_url,
        summary=data.summary,
        photos=data.photos or [],
        raw_data=data.raw_data or {},
        chinese_focus_summary=data.chinese_focus_summary,
        pros=data.pros or [],
        cons=data.cons or [],
        review_snippets=data.review_snippets or [],
    )
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def update_candidate(
    db: AsyncSession, candidate: Candidate, data: CandidateUpdate
) -> Candidate:
    if data.tier is not None:
        candidate.tier = CandidateTier(data.tier)
    if data.name is not None:
        candidate.name = data.name
    if data.area is not None:
        candidate.area = data.area
    if data.summary is not None:
        candidate.summary = data.summary
    if data.pros is not None:
        candidate.pros = data.pros
    if data.cons is not None:
        candidate.cons = data.cons
    if data.review_snippets is not None:
        candidate.review_snippets = data.review_snippets
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def delete_candidate(db: AsyncSession, candidate: Candidate) -> None:
    await db.delete(candidate)
    await db.flush()


# Votes


async def get_vote_counts(db: AsyncSession, candidate_id: int) -> dict[str, int]:
    result = await db.execute(
        select(Vote.vote_type, func.count(Vote.id))
        .where(Vote.candidate_id == candidate_id)
        .group_by(Vote.vote_type)
    )
    counts = {row[0].value: row[1] for row in result.all()}
    return {
        "like_count": counts.get("like", 0),
        "dislike_count": counts.get("dislike", 0),
        "neutral_count": counts.get("neutral", 0),
    }


async def get_vote_by_session(
    db: AsyncSession, candidate_id: int, session_id: str
) -> Vote | None:
    result = await db.execute(
        select(Vote).where(Vote.candidate_id == candidate_id, Vote.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def cast_vote(
    db: AsyncSession, candidate_id: int, session_id: str, data: VoteCreate
) -> Vote:
    existing = await get_vote_by_session(db, candidate_id, session_id)
    if existing:
        existing.vote_type = VoteType(data.vote_type)
        await db.flush()
        await db.refresh(existing)
        return existing
    vote = Vote(
        candidate_id=candidate_id,
        session_id=session_id,
        vote_type=VoteType(data.vote_type),
    )
    db.add(vote)
    try:
        # Savepoint so a concurrent insert of the same (candidate, session)
        # only rolls back this insert, not the request's transaction.
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        # Lost the race against a concurrent vote from the same session;
        # fall back to updating the row that won.
        existing = await get_vote_by_session(db, candidate_id, session_id)
        if existing is None:  # winner not committed yet — surface as conflict
            raise
        existing.vote_type = VoteType(data.vote_type)
        await db.flush()
        return existing
    await db.refresh(vote)
    return vote


# Collection runs


async def create_collection_run(db: AsyncSession, project_id: int) -> CollectionRun:
    run = CollectionRun(
        project_id=project_id,
        status=CollectionStatus.pending,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


# Reports


async def get_or_create_report(db: AsyncSession, project_id: int) -> Report:
    result = await db.execute(select(Report).where(Report.project_id == project_id))
    report = result.scalar_one_or_none()
    if not report:
        report = Report(project_id=project_id, status=CollectionStatus.pending, progress=0)
        db.add(report)
        await db.flush()
        await db.refresh(report)
    return report
