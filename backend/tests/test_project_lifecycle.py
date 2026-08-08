import pytest

from tests.contract_support import route_paths, table

pytestmark = pytest.mark.no_db


def test_project_has_soft_delete_recovery_and_execution_fence_state():
    projects = table("projects")
    assert projects is not None
    required = {"deleted_at", "purge_after", "share_token_version", "execution_fence_version"}
    assert required <= set(projects.columns.keys())


def test_delete_recover_and_token_scoped_sse_routes_exist():
    paths = route_paths()
    expected = {
        "/api/projects/by-token/{share_token}/delete",
        "/api/projects/by-token/{share_token}/recover",
        "/api/projects/by-token/{share_token}/report/stream",
    }
    assert expected <= paths


def test_lifecycle_models_can_fence_active_work_and_purge_dependents():
    runs = table("collection_runs")
    outbox = table("task_outbox")
    assert runs is not None and outbox is not None
    assert {"cancelled_at", "execution_fence_version"} <= set(runs.columns.keys())
    assert "cancelled_at" in outbox.columns
