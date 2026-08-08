"""Single atomic budget gate for all paid provider requests."""

import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Awaitable, Callable, TypeVar

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CollectionRun, ExternalCallReservation, Project

T = TypeVar("T")
BATCH_REQUEST_LIMIT = 150
LIFETIME_REQUEST_LIMIT = 500
LIFETIME_COST_USD = Decimal("2")
PROVIDER_BATCH_LIMIT = 40
PROVIDER_LIFETIME_LIMIT = 150
PROVIDER_REQUEST_SHARE = Decimal("0.40")
PROVIDER_COST_SHARE = Decimal("0.50")


class BudgetExhaustedError(Exception):
    """A stable domain result; callers should retain partial data."""


class OperationInProgressError(Exception):
    """The same logical provider operation is already owned elsewhere."""


def _encode_result(result):
    from app.collectors.base import CollectorResult

    if isinstance(result, CollectorResult):
        return {"kind": "collector_result", "value": result.to_dict()}
    return {"kind": "json", "value": result}


def _decode_result(payload):
    if not payload:
        raise OperationInProgressError("provider_result_unavailable")
    if payload.get("kind") == "collector_result":
        from app.collectors.base import CollectorResult

        return CollectorResult(**payload["value"])
    return payload.get("value")


async def _totals(db: AsyncSession, *filters) -> tuple[int, Decimal]:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(ExternalCallReservation.request_units), 0),
                func.coalesce(func.sum(ExternalCallReservation.estimated_cost_usd), 0),
            ).where(*filters)
        )
    ).one()
    return int(row[0]), Decimal(row[1])


async def reserve(
    db: AsyncSession,
    *,
    project_id: int,
    run_id: int,
    provider: str,
    idempotency_key: str,
    request_units: int = 1,
    estimated_cost_usd: Decimal = Decimal("0"),
) -> ExternalCallReservation:
    existing = await db.scalar(
        select(ExternalCallReservation).where(
            ExternalCallReservation.idempotency_key == idempotency_key
        )
    )
    if existing:
        return existing

    project = await db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    # Recheck after obtaining the project lock: a concurrent transaction may
    # have committed the same logical reservation while this one waited.
    existing = await db.scalar(
        select(ExternalCallReservation).where(
            ExternalCallReservation.idempotency_key == idempotency_key
        )
    )
    if existing:
        return existing
    run = await db.get(CollectionRun, run_id)
    if (
        not project
        or not run
        or project.deleted_at
        or run.execution_fence_version != project.execution_fence_version
    ):
        raise BudgetExhaustedError("execution_revoked")

    life_units, life_cost = await _totals(db, ExternalCallReservation.project_id == project_id)
    batch_units, _ = await _totals(db, ExternalCallReservation.run_id == run_id)
    provider_life, provider_cost = await _totals(
        db,
        ExternalCallReservation.project_id == project_id,
        ExternalCallReservation.provider == provider,
    )
    provider_batch, _ = await _totals(
        db,
        ExternalCallReservation.run_id == run_id,
        ExternalCallReservation.provider == provider,
    )
    next_life = life_units + request_units
    next_cost = life_cost + estimated_cost_usd
    if (
        batch_units + request_units > BATCH_REQUEST_LIMIT
        or next_life > LIFETIME_REQUEST_LIMIT
        or next_cost > LIFETIME_COST_USD
        or provider_batch + request_units > PROVIDER_BATCH_LIMIT
        or provider_life + request_units > PROVIDER_LIFETIME_LIMIT
        or provider_life + request_units > int(LIFETIME_REQUEST_LIMIT * PROVIDER_REQUEST_SHARE)
        or provider_cost + estimated_cost_usd > LIFETIME_COST_USD * PROVIDER_COST_SHARE
    ):
        raise BudgetExhaustedError("budget_exhausted")

    reservation = ExternalCallReservation(
        project_id=project_id,
        run_id=run_id,
        provider=provider,
        idempotency_key=idempotency_key,
        request_units=request_units,
        estimated_cost_usd=estimated_cost_usd,
    )
    db.add(reservation)
    await db.flush()
    return reservation


async def send(operation: Callable[[], Awaitable[T]], *, reservation: object) -> T:
    if os.getenv("DENY_EXTERNAL_NETWORK") == "1":
        raise RuntimeError("external_network_denied")
    return await operation()


async def budgeted_send(
    operation: Callable[[], Awaitable[T]],
    *,
    db: AsyncSession,
    expected_run_owner: str | None = None,
    **context,
) -> T:
    reservation = await reserve(db, **context)
    # The reservation must be durable before a provider can observe the call.
    # Committing here also releases the project budget lock so deletion can
    # advance the execution fence while a slow provider request is in flight.
    await db.commit()
    owner = secrets.token_hex(16)
    claimed = await db.scalar(
        update(ExternalCallReservation)
        .where(
            ExternalCallReservation.id == reservation.id,
            ExternalCallReservation.status == "reserved",
            ExternalCallReservation.operation_owner.is_(None),
        )
        .values(
            status="sending",
            operation_owner=owner,
            operation_started_at=datetime.now(timezone.utc),
        )
        .returning(ExternalCallReservation.id)
    )
    await db.commit()
    if not claimed:
        await db.refresh(reservation)
        if reservation.status == "succeeded":
            return _decode_result(reservation.response_payload)
        raise OperationInProgressError("provider_operation_already_claimed")

    # Hold the project row through the actual send. Deletion/fence advancement
    # either commits before this check (send=0), or waits until this operation
    # has durably recorded its outcome.
    project = await db.scalar(
        select(Project)
        .where(Project.id == reservation.project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    run = await db.scalar(
        select(CollectionRun)
        .where(CollectionRun.id == reservation.run_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    await db.refresh(reservation)
    if (
        not project
        or not run
        or project.deleted_at
        or run.execution_fence_version != project.execution_fence_version
        or (expected_run_owner is not None and run.lease_owner != expected_run_owner)
        or reservation.operation_owner != owner
        or reservation.status != "sending"
    ):
        reservation.status = "revoked"
        await db.commit()
        raise BudgetExhaustedError("execution_revoked")
    try:
        result = await send(operation, reservation=reservation)
    except Exception:
        reservation.status = "failed"
        await db.commit()
        raise
    reservation.status = "succeeded"
    reservation.response_payload = _encode_result(result)
    await db.commit()
    return result
