import asyncio
import os
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import CREATOR_COOKIE, secret_hash
from app.database import get_db
from app.main import app
from app.models import CollectionRun, CollectionStatus, Project, TaskOutbox
from app.services.provider_transport import BudgetExhaustedError, reserve
from app.services.rate_limits import _enforce


@pytest.mark.asyncio
async def test_provider_batch_budget_rejects_41st_before_send(db_session):
    project = Project(
        destination="Budget City",
        duration_days=2,
        departure="A",
        share_token_hash=uuid.uuid4().hex,
        creator_credential_hash=uuid.uuid4().hex,
        recovery_key_hash=uuid.uuid4().hex,
    )
    db_session.add(project)
    await db_session.flush()
    run = CollectionRun(
        project_id=project.id,
        status=CollectionStatus.running,
        execution_fence_version=project.execution_fence_version,
    )
    db_session.add(run)
    await db_session.commit()
    for index in range(40):
        await reserve(
            db_session,
            project_id=project.id,
            run_id=run.id,
            provider="fixture",
            idempotency_key=f"{run.id}:fixture:{index}",
            estimated_cost_usd=Decimal("0.001"),
        )
        await db_session.commit()
    with pytest.raises(BudgetExhaustedError, match="budget_exhausted"):
        await reserve(
            db_session,
            project_id=project.id,
            run_id=run.id,
            provider="fixture",
            idempotency_key=f"{run.id}:fixture:40",
        )


@pytest.mark.asyncio
async def test_real_redis_rolling_window_boundary(monkeypatch):
    redis_url = os.getenv("TRAVEL_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("TRAVEL_TEST_REDIS_URL is required for the disposable Redis test")
    from app.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_REDIS_URL", redis_url)
    key = uuid.uuid4().hex
    for _ in range(3):
        await _enforce("dynamic", key, ((60, 3),))
    with pytest.raises(HTTPException) as exc:
        await _enforce("dynamic", key, ((60, 3),))
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_20_concurrent_recollects_reuse_one_run_and_outbox(db_session):
    share_token = uuid.uuid4().hex
    creator = uuid.uuid4().hex
    project = Project(
        destination="Concurrent City",
        duration_days=2,
        departure="A",
        share_token_hash=secret_hash(share_token),
        creator_credential_hash=secret_hash(creator),
        recovery_key_hash=uuid.uuid4().hex,
    )
    db_session.add(project)
    await db_session.commit()
    project_id = project.id

    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def isolated_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = isolated_db
    path = f"/api/projects/by-token/{share_token}"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://test",
            headers={
                "Origin": "http://localhost:3000",
                "Cookie": f"{CREATOR_COOKIE}={creator}",
            },
        ) as client:
            responses = await asyncio.gather(
                *(client.post(f"{path}/recollect", json={}) for _ in range(20))
            )
        assert {response.status_code for response in responses} == {200}
    finally:
        app.dependency_overrides.clear()

    run_count = await db_session.scalar(
        select(func.count(CollectionRun.id)).where(CollectionRun.project_id == project_id)
    )
    outbox_count = await db_session.scalar(
        select(func.count(TaskOutbox.id)).where(TaskOutbox.project_id == project_id)
    )
    assert run_count == 1
    assert outbox_count == 1
