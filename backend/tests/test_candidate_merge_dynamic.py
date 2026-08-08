import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import (
    Candidate,
    CandidateFieldOverride,
    CandidateMergeAudit,
    CandidateSource,
    Project,
    Vote,
    VoteMergeConflictAudit,
    VoteType,
)
from app.services.candidate_merge import merge_candidates


async def _merge_fixture(db_session):
    project = Project(
        destination="Merge City",
        duration_days=2,
        departure="A",
        share_token_hash=uuid.uuid4().hex,
        creator_credential_hash=uuid.uuid4().hex,
        recovery_key_hash=uuid.uuid4().hex,
    )
    db_session.add(project)
    await db_session.flush()
    older = Candidate(
        project_id=project.id,
        name="Older",
        category="cultural",
        tier="optional",
        source="fixture",
        origin="automatic",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    protected = Candidate(
        project_id=project.id,
        name="Protected",
        category="cultural",
        tier="optional",
        source="fixture",
        origin="automatic",
    )
    db_session.add_all([older, protected])
    await db_session.flush()
    db_session.add_all(
        [
            CandidateFieldOverride(
                candidate_id=older.id, field_name="name", value="Older override", version=2
            ),
            CandidateFieldOverride(
                candidate_id=protected.id,
                field_name="name",
                value="Protected override",
                version=3,
            ),
            CandidateSource(
                project_id=project.id,
                candidate_id=protected.id,
                identity_provider="fixture",
                entity_type="cultural",
                external_id="protected-1",
            ),
            Vote(
                candidate_id=older.id,
                session_id="legacy-a",
                voter_hash="same-voter",
                vote_type=VoteType.like,
                updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
            Vote(
                candidate_id=protected.id,
                session_id="legacy-b",
                voter_hash="same-voter",
                vote_type=VoteType.dislike,
                updated_at=datetime.now(timezone.utc),
            ),
        ]
    )
    await db_session.commit()
    return project, older, protected


@pytest.mark.asyncio
async def test_merge_freezes_survivor_override_and_vote_decisions(db_session):
    project, older, protected = await _merge_fixture(db_session)
    survivor = await merge_candidates(db_session, project.id, older.id, protected.id)
    await db_session.commit()
    assert survivor.id == protected.id
    audit = await db_session.scalar(select(CandidateMergeAudit))
    assert audit.evidence["strategy"] == "manual_then_reference_count_then_oldest"
    conflict = audit.evidence["override_conflicts"][0]
    assert conflict["kept"]["value"] == "Protected override"
    assert conflict["discarded"]["value"] == "Older override"
    vote_audit = await db_session.scalar(select(VoteMergeConflictAudit))
    assert vote_audit.evidence["kept"]["value"] == "dislike"
    assert vote_audit.evidence["discarded"]["value"] == "like"
    assert await db_session.scalar(select(func.count(Vote.id))) == 1


@pytest.mark.asyncio
async def test_merge_failure_rolls_back_all_references(db_session, monkeypatch):
    project, older, protected = await _merge_fixture(db_session)
    project_id = project.id
    candidate_ids = [older.id, protected.id]
    original_flush = db_session.flush
    calls = 0

    async def fail_second_flush(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected_merge_failure")
        return await original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", fail_second_flush)
    with pytest.raises(RuntimeError, match="injected_merge_failure"):
        await merge_candidates(db_session, project.id, older.id, protected.id)
    await db_session.rollback()
    assert await db_session.scalar(
        select(func.count(Candidate.id)).where(Candidate.id.in_(candidate_ids))
    ) == 2
    assert await db_session.scalar(
        select(func.count(Vote.id)).where(Vote.candidate_id.in_(candidate_ids))
    ) == 2
    assert await db_session.scalar(
        select(func.count(CandidateFieldOverride.id)).where(
            CandidateFieldOverride.candidate_id.in_(candidate_ids)
        )
    ) == 2
    assert await db_session.scalar(
        select(func.count(CandidateMergeAudit.id)).where(
            CandidateMergeAudit.project_id == project_id
        )
    ) == 0
