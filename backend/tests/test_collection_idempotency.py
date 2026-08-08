import pytest

from tests.contract_support import table

pytestmark = pytest.mark.no_db


def test_active_run_outbox_and_lease_contract_is_persisted():
    runs = table("collection_runs")
    outbox = table("task_outbox")
    assert runs is not None and outbox is not None
    assert {"lease_expires_at", "heartbeat_at", "attempt_count", "execution_fence_version"} <= set(
        runs.columns.keys()
    )
    assert {"run_id", "dispatched_at", "available_at", "attempt_count"} <= set(
        outbox.columns.keys()
    )


def test_database_declares_one_active_run_per_project():
    runs = table("collection_runs")
    assert runs is not None
    indexes = {index.name: str(index.dialect_options) for index in runs.indexes}
    assert "uq_collection_runs_one_active_per_project" in indexes
