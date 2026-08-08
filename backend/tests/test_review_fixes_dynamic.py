import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from app.auth import CREATOR_COOKIE
from app.collectors import registry
from app.collectors.base import CollectorResult
from app.config import settings
from app.models import (
    Candidate,
    CollectionRun,
    CollectionStatus,
    ExternalCallReservation,
    Project,
    TaskOutbox,
)
from app.services.collection import run_collection_pipeline
from app.services.provider_transport import BudgetExhaustedError, budgeted_send, reserve
from app.services.rate_limits import trusted_client_ip
from app.services.report import ReportBuilder
from app.services.run_execution import claim_run
from app.tasks.maintenance import recover_stale_runs


async def _owned_run(db_session):
    project = Project(
        destination="Review City",
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
        status=CollectionStatus.pending,
        execution_fence_version=project.execution_fence_version,
    )
    db_session.add(run)
    await db_session.commit()
    claimed = await claim_run(db_session, run.id)
    await db_session.commit()
    return project, claimed


@pytest.mark.asyncio
async def test_provider_duplicate_delivery_reuses_durable_result(db_session, monkeypatch):
    monkeypatch.delenv("DENY_EXTERNAL_NETWORK", raising=False)
    project, run = await _owned_run(db_session)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        return CollectorResult("fixture", True, [{"name": "Only once"}])

    context = {
        "project_id": project.id,
        "run_id": run.id,
        "provider": "fixture",
        "idempotency_key": f"{run.id}:fixture:once",
        "expected_run_owner": run.lease_owner,
    }
    first = await budgeted_send(operation, db=db_session, **context)
    second = await budgeted_send(operation, db=db_session, **context)
    assert calls == 1
    assert first.to_dict() == second.to_dict()
    assert await db_session.scalar(
        select(func.count(ExternalCallReservation.id)).where(
            ExternalCallReservation.project_id == project.id
        )
    ) == 1


@pytest.mark.asyncio
async def test_delete_committed_after_reservation_prevents_send(db_session, monkeypatch):
    monkeypatch.delenv("DENY_EXTERNAL_NETWORK", raising=False)
    project, run = await _owned_run(db_session)
    key = f"{run.id}:fixture:delete-fence"
    await reserve(
        db_session,
        project_id=project.id,
        run_id=run.id,
        provider="fixture",
        idempotency_key=key,
    )
    await db_session.commit()
    project.deleted_at = datetime.now(timezone.utc)
    project.execution_fence_version += 1
    await db_session.commit()
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        return {"unexpected": True}

    with pytest.raises(BudgetExhaustedError, match="execution_revoked"):
        await budgeted_send(
            operation,
            db=db_session,
            project_id=project.id,
            run_id=run.id,
            provider="fixture",
            idempotency_key=key,
            expected_run_owner=run.lease_owner,
        )
    assert calls == 0


@pytest.mark.asyncio
async def test_expired_lease_is_requeued_once_and_reclaimable(db_session):
    project, run = await _owned_run(db_session)
    run.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()
    assert await recover_stale_runs(db_session) == 1
    assert await recover_stale_runs(db_session) == 0
    await db_session.refresh(run)
    assert run.status == CollectionStatus.pending and run.lease_owner is None
    retry = await db_session.scalar(
        select(TaskOutbox).where(TaskOutbox.dedupe_key.like(f"collection:{run.id}:attempt:%"))
    )
    assert retry is not None
    assert await claim_run(db_session, run.id) is not None


@pytest.mark.asyncio
async def test_active_project_recovery_reissues_creator_cookie(client):
    created = (
        await client.post(
            "/api/projects",
            json={"destination": "Recovery City", "duration_days": 2, "departure": "A"},
        )
    ).json()
    client.cookies.clear()
    root = f"/api/projects/by-token/{created['share_token']}"
    check = (await client.get(f"{root}/creator-check")).json()
    assert check == {"creator": False, "recovery_required": True}
    recovered = await client.post(f"{root}/recover", json={"recovery_key": created["recovery_key"]})
    assert recovered.status_code == 200
    assert recovered.json()["share_token"] == created["share_token"]
    assert CREATOR_COOKIE in recovered.cookies
    assert (await client.get(f"{root}/creator-check")).json()["creator"] is True


@pytest.mark.asyncio
async def test_request_logs_never_capture_share_token(client, caplog):
    token = "log-secret-" + uuid.uuid4().hex
    caplog.set_level(logging.INFO)
    await client.get(f"/api/projects/by-token/{token}")
    assert token not in caplog.text
    assert "/api/projects/by-token/{share_token}" in caplog.text


def test_forwarded_chain_peels_trusted_hops_and_rejects_malformed(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", "10.0.0.0/8,192.0.2.0/24")

    def request(value: str) -> Request:
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [(b"x-forwarded-for", value.encode())],
                "client": ("10.0.0.8", 1234),
            }
        )

    assert trusted_client_ip(request("203.0.113.99, 198.51.100.7, 192.0.2.9")) == "198.51.100.7"
    with pytest.raises(Exception) as exc:
        trusted_client_ip(request("not-an-ip, 192.0.2.9"))
    assert getattr(exc.value, "status_code", None) == 400
    assert getattr(exc.value, "detail", None) == "invalid_forwarded_chain"


@pytest.mark.asyncio
async def test_report_builder_uses_effective_override_projection(db_session, monkeypatch):
    monkeypatch.setattr("app.services.report.llm_client.api_key", "")
    project, run = await _owned_run(db_session)
    projection = [
        {
            "id": 1,
            "name": "人工覆盖名称",
            "category": "cultural",
            "tier": "must_go",
            "area": "覆盖区域",
            "raw_data": {},
        }
    ]
    report = await ReportBuilder(
        project,
        projection,
        db=db_session,
        run_id=run.id,
        expected_version=project.candidate_data_version,
    ).build()
    assert report["important_experiences"]["cultural"][0]["name"] == "人工覆盖名称"


@pytest.mark.asyncio
async def test_identical_second_collection_keeps_version_and_report_outbox(db_session, monkeypatch):
    monkeypatch.delenv("DENY_EXTERNAL_NETWORK", raising=False)
    monkeypatch.setattr("app.services.review_insights.llm_client.api_key", "")

    class StableCollector:
        name = "stable_fixture"

        async def is_available(self):
            return True

        async def collect_broad(self, destination, project_data):
            return CollectorResult(
                self.name,
                True,
                [
                    {
                        "name": "Stable Museum",
                        "source": self.name,
                        "identity_provider": self.name,
                        "external_id": "stable-1",
                        "entity_type": "cultural",
                        "address": "1 Stable Road",
                    }
                ],
            )

        async def collect_detail(self, candidate, project_data):
            return CollectorResult(self.name, True, {})

    monkeypatch.setattr(registry, "all_collectors", lambda: [StableCollector()])
    project, first_run = await _owned_run(db_session)
    await run_collection_pipeline(db_session, project, first_run)
    await db_session.refresh(project)
    first_version = project.candidate_data_version
    first_report_count = await db_session.scalar(
        select(func.count(TaskOutbox.id)).where(
            TaskOutbox.project_id == project.id,
            TaskOutbox.task_name == "app.tasks.report.generate_report",
        )
    )

    second_run = CollectionRun(
        project_id=project.id,
        status=CollectionStatus.pending,
        execution_fence_version=project.execution_fence_version,
    )
    db_session.add(second_run)
    await db_session.commit()
    second_run = await claim_run(db_session, second_run.id)
    await db_session.commit()
    await run_collection_pipeline(db_session, project, second_run)
    await db_session.refresh(project)
    second_report_count = await db_session.scalar(
        select(func.count(TaskOutbox.id)).where(
            TaskOutbox.project_id == project.id,
            TaskOutbox.task_name == "app.tasks.report.generate_report",
        )
    )
    assert project.candidate_data_version == first_version
    assert first_report_count == second_report_count == 1


@pytest.mark.asyncio
async def test_delete_during_persistence_rolls_back_candidates_and_report_intent(
    db_session, monkeypatch
):
    monkeypatch.delenv("DENY_EXTERNAL_NETWORK", raising=False)
    monkeypatch.setattr("app.services.review_insights.llm_client.api_key", "")

    class SlowBoundaryCollector:
        name = "delete_race_fixture"

        async def is_available(self):
            return True

        async def collect_broad(self, destination, project_data):
            return CollectorResult(
                self.name,
                True,
                [
                    {
                        "name": "Must Roll Back",
                        "source": self.name,
                        "identity_provider": self.name,
                        "external_id": "delete-race-1",
                        "entity_type": "cultural",
                    }
                ],
            )

        async def collect_detail(self, candidate, project_data):
            return CollectorResult(self.name, True, {})

    monkeypatch.setattr(registry, "all_collectors", lambda: [SlowBoundaryCollector()])
    project, run = await _owned_run(db_session)
    project_id = project.id
    original = __import__(
        "app.services.collection", fromlist=["ingest_candidate_source"]
    ).ingest_candidate_source
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def delete_after_staging(db, *args, **kwargs):
        candidate = await original(db, *args, **kwargs)
        async with session_factory() as other:
            await other.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(
                    deleted_at=datetime.now(timezone.utc),
                    execution_fence_version=Project.execution_fence_version + 1,
                )
            )
            await other.commit()
        return candidate

    monkeypatch.setattr("app.services.collection.ingest_candidate_source", delete_after_staging)
    result = await run_collection_pipeline(db_session, project, run)
    assert result == {"status": "revoked"}
    assert (
        await db_session.scalar(
            select(func.count(Candidate.id)).where(Candidate.project_id == project_id)
        )
        == 0
    )
    assert (
        await db_session.scalar(
            select(func.count(TaskOutbox.id)).where(TaskOutbox.project_id == project_id)
        )
        == 0
    )
