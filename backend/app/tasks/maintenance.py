import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import CollectionRun, CollectionStatus, Project, TaskOutbox


async def recover_stale_runs(db: AsyncSession) -> int:
    """CAS expired run leases back to pending and enqueue one retry intent."""
    now = datetime.now(timezone.utc)
    runs = list(
        (
            await db.execute(
                select(CollectionRun)
                .where(
                    CollectionRun.status == CollectionStatus.running,
                    CollectionRun.lease_expires_at <= now,
                )
                .with_for_update(skip_locked=True)
            )
        ).scalars()
    )
    for run in runs:
        run.status = CollectionStatus.pending
        run.lease_owner = None
        run.lease_expires_at = None
        await db.execute(
            pg_insert(TaskOutbox)
            .values(
                project_id=run.project_id,
                run_id=run.id,
                task_name="app.tasks.collection.run_collection",
                dedupe_key=f"collection:{run.id}:attempt:{run.attempt_count + 1}",
                payload={"args": [run.project_id, run.id]},
            )
            .on_conflict_do_nothing(index_elements=[TaskOutbox.dedupe_key])
        )
    await db.commit()
    return len(runs)


@celery_app.task(name="app.tasks.maintenance.purge_expired_projects")
def purge_expired_projects() -> int:
    """Physically purge soft-deleted projects after their 30-day window."""

    async def _purge() -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Project)
                .where(
                    Project.deleted_at.is_not(None),
                    Project.purge_after <= datetime.now(timezone.utc),
                )
                .returning(Project.id)
            )
            count = len(result.scalars().all())
            await session.commit()
            return count

    return asyncio.run(_purge())


@celery_app.task(name="app.tasks.maintenance.recover_stale_collection_runs")
def recover_stale_collection_runs() -> int:
    async def _recover() -> int:
        async with AsyncSessionLocal() as session:
            return await recover_stale_runs(session)

    return asyncio.run(_recover())
