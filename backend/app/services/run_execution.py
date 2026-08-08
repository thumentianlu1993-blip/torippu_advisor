"""Database-backed run lease and outbox primitives."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CollectionRun, CollectionStatus, TaskOutbox


async def claim_run(
    db: AsyncSession, run_id: int, lease_seconds: int = 120
) -> CollectionRun | None:
    now = datetime.now(timezone.utc)
    run = await db.scalar(select(CollectionRun).where(CollectionRun.id == run_id).with_for_update())
    if not run or run.status not in {CollectionStatus.pending, CollectionStatus.running}:
        return None
    if run.lease_expires_at and run.lease_expires_at > now:
        return None
    run.status = CollectionStatus.running
    run.attempt_count += 1
    run.lease_owner = secrets.token_hex(16)
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await db.flush()
    return run


async def heartbeat_run(
    db: AsyncSession,
    run: CollectionRun,
    expected_owner: str,
    lease_seconds: int = 180,
) -> bool:
    now = datetime.now(timezone.utc)
    await db.refresh(run)
    if (
        run.status != CollectionStatus.running
        or run.lease_owner != expected_owner
        or (run.lease_expires_at and run.lease_expires_at <= now)
    ):
        return False
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await db.flush()
    return True


async def claim_outbox(db: AsyncSession, limit: int = 20) -> list[TaskOutbox]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(TaskOutbox)
        .where(
            TaskOutbox.dispatched_at.is_(None),
            TaskOutbox.cancelled_at.is_(None),
            TaskOutbox.available_at <= now,
        )
        .with_for_update(skip_locked=True)
        .limit(limit)
    )
    return list(result.scalars())
