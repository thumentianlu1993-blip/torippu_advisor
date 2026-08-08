import asyncio
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.run_execution import claim_outbox


@celery_app.task(name="app.tasks.outbox.dispatch_task_outbox")
def dispatch_task_outbox() -> int:
    """Dispatch committed task intents with retryable, skip-locked claims."""

    async def _dispatch() -> int:
        dispatched = 0
        async with AsyncSessionLocal() as session:
            rows = await claim_outbox(session)
            for row in rows:
                try:
                    celery_app.send_task(row.task_name, args=row.payload.get("args", []))
                except Exception:  # noqa: BLE001
                    row.attempt_count += 1
                    delay = min(300, 2 ** min(row.attempt_count, 8))
                    row.available_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                else:
                    row.dispatched_at = datetime.now(timezone.utc)
                    dispatched += 1
            await session.commit()
        return dispatched

    return asyncio.run(_dispatch())
