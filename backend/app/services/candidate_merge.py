"""Transactional candidate merge with vote-conflict audit."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Candidate,
    CandidateFieldOverride,
    CandidateMergeAudit,
    CandidateSource,
    Image,
    MergeProposal,
    Vote,
    VoteMergeConflictAudit,
)


async def merge_candidates(
    db: AsyncSession, project_id: int, first_id: int, second_id: int
) -> Candidate:
    rows = list(
        (
            await db.execute(
                select(Candidate)
                .where(
                    Candidate.project_id == project_id,
                    Candidate.id.in_([first_id, second_id]),
                )
                .with_for_update()
            )
        ).scalars()
    )
    if len(rows) != 2:
        raise ValueError("candidate_not_found")
    reference_counts: dict[int, int] = {}
    for item in rows:
        vote_count = await db.scalar(
            select(func.count(Vote.id)).where(Vote.candidate_id == item.id)
        )
        override_count = await db.scalar(
            select(func.count(CandidateFieldOverride.id)).where(
                CandidateFieldOverride.candidate_id == item.id
            )
        )
        source_count = await db.scalar(
            select(func.count(CandidateSource.id)).where(CandidateSource.candidate_id == item.id)
        )
        image_count = await db.scalar(
            select(func.count(Image.id)).where(Image.candidate_id == item.id)
        )
        reference_counts[item.id] = int(vote_count + override_count + source_count + image_count)
    rows.sort(
        key=lambda item: (
            -(item.origin == "manual"),
            -reference_counts[item.id],
            item.created_at,
            item.id,
        )
    )
    survivor, loser = rows
    audit = CandidateMergeAudit(
        project_id=project_id,
        survivor_candidate_id=survivor.id,
        loser_candidate_id=loser.id,
        evidence={
            "strategy": "manual_then_reference_count_then_oldest",
            "reference_counts": reference_counts,
            "override_conflicts": [],
            "vote_conflicts": [],
        },
    )
    db.add(audit)
    await db.flush()

    survivor_votes = {
        vote.voter_hash: vote
        for vote in (
            await db.execute(select(Vote).where(Vote.candidate_id == survivor.id))
        ).scalars()
    }
    loser_votes = list(
        (await db.execute(select(Vote).where(Vote.candidate_id == loser.id))).scalars()
    )
    for vote in loser_votes:
        conflict = survivor_votes.get(vote.voter_hash)
        if not conflict:
            vote.candidate_id = survivor.id
            continue
        kept, discarded = (
            (vote, conflict)
            if (vote.updated_at, vote.id) > (conflict.updated_at, conflict.id)
            else (conflict, vote)
        )
        if kept is vote:
            await db.delete(conflict)
            vote.candidate_id = survivor.id
        else:
            await db.delete(vote)
        db.add(
            VoteMergeConflictAudit(
                merge_audit_id=audit.id,
                kept_vote_id=kept.id,
                discarded_vote_id=discarded.id,
                evidence={
                    "rule": "latest_updated_at_then_id",
                    "kept": {
                        "id": kept.id,
                        "value": kept.vote_type.value,
                        "voter_hash": kept.voter_hash,
                        "updated_at": kept.updated_at.isoformat(),
                    },
                    "discarded": {
                        "id": discarded.id,
                        "value": discarded.vote_type.value,
                        "voter_hash": discarded.voter_hash,
                        "updated_at": discarded.updated_at.isoformat(),
                    },
                },
            )
        )

    survivor_override_rows = list(
        (
            await db.execute(
                select(CandidateFieldOverride).where(
                    CandidateFieldOverride.candidate_id == survivor.id
                )
            )
        ).scalars()
    )
    survivor_overrides = {item.field_name: item for item in survivor_override_rows}
    loser_overrides = list(
        (
            await db.execute(
                select(CandidateFieldOverride).where(
                    CandidateFieldOverride.candidate_id == loser.id
                )
            )
        ).scalars()
    )
    for override in loser_overrides:
        if override.field_name in survivor_overrides:
            kept_override = survivor_overrides[override.field_name]
            evidence = dict(audit.evidence)
            evidence["override_conflicts"] = [
                *evidence.get("override_conflicts", []),
                {
                    "field_name": override.field_name,
                    "rule": "survivor_override_preserved",
                    "kept": {
                        "id": kept_override.id,
                        "value": kept_override.value,
                        "version": kept_override.version,
                    },
                    "discarded": {
                        "id": override.id,
                        "value": override.value,
                        "version": override.version,
                    },
                },
            ]
            audit.evidence = evidence
            await db.delete(override)
        else:
            override.candidate_id = survivor.id

    survivor_sources = {
        (
            source.identity_provider,
            source.entity_type,
            source.external_id,
            source.fallback_fingerprint,
        )
        for source in (
            await db.execute(
                select(CandidateSource).where(CandidateSource.candidate_id == survivor.id)
            )
        ).scalars()
    }
    loser_sources = list(
        (
            await db.execute(
                select(CandidateSource).where(CandidateSource.candidate_id == loser.id)
            )
        ).scalars()
    )
    for source in loser_sources:
        key = (
            source.identity_provider,
            source.entity_type,
            source.external_id,
            source.fallback_fingerprint,
        )
        if key in survivor_sources:
            await db.delete(source)
        else:
            source.candidate_id = survivor.id
    await db.execute(
        update(Image).where(Image.candidate_id == loser.id).values(candidate_id=survivor.id)
    )
    loser.active = False
    loser.version += 1
    survivor.version += 1
    await db.flush()
    return survivor


async def decide_proposal(
    db: AsyncSession, project_id: int, proposal_id: int, decision: str
) -> MergeProposal:
    proposal = await db.scalar(
        select(MergeProposal)
        .where(MergeProposal.id == proposal_id, MergeProposal.project_id == project_id)
        .with_for_update()
    )
    if not proposal or proposal.status != "pending":
        raise ValueError("proposal_not_found")
    if decision == "merge":
        await merge_candidates(db, project_id, proposal.candidate_a_id, proposal.candidate_b_id)
        proposal.status = "merged"
    elif decision == "keep_separate":
        proposal.status = "kept_separate"
    else:
        raise ValueError("invalid_decision")
    return proposal
