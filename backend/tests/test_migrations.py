import ast

import pytest

from tests.contract_support import REPO_ROOT, source

pytestmark = pytest.mark.no_db


def test_historical_creator_migration_is_nullable_first_and_backfills_before_not_null():
    migration = source("backend/alembic/versions/b1270b2f0ef9_add_project_creator_token.py")
    add_index = migration.index("op.add_column('projects', sa.Column('creator_token'")
    assert "nullable=True" in migration[add_index : add_index + 180]
    assert "UPDATE projects" in migration
    assert migration.index("UPDATE projects") < migration.index("nullable=False", add_index)


def test_migration_runner_refuses_unmarked_or_non_prefixed_database():
    script_path = REPO_ROOT / "scripts/ci/test-migrations.sh"
    assert script_path.exists()
    script = script_path.read_text(encoding="utf-8")
    assert "TRAVEL_DISPOSABLE_DB" in script
    assert "travel_test_" in script
    assert "DATABASE_URL" not in script or "TRAVEL_TEST_DATABASE_URL" in script
    assert "alembic downgrade" in script and "alembic upgrade" in script


def test_bridge_contract_artifact_is_importable_and_declares_fail_closed_writes():
    bridge_path = REPO_ROOT / "backend/app/bridge_contract.py"
    assert bridge_path.exists()
    ast.parse(bridge_path.read_text(encoding="utf-8"))
    bridge = bridge_path.read_text(encoding="utf-8")
    assert "expand" in bridge
    assert "fail_closed" in bridge
    assert "creator" in bridge and "collection" in bridge


def test_expand_migration_uses_explicit_alembic_operations_only():
    migration = source("backend/alembic/versions/d88f6fdd4c31_stabilize_current_mvp_expand.py")
    assert "Base.metadata.create_all" not in migration
    for table_name in (
        "task_outbox",
        "external_call_reservations",
        "candidate_sources",
        "source_observations",
        "merge_proposals",
        "candidate_merge_audits",
        "vote_merge_conflict_audits",
        "candidate_field_overrides",
        "candidate_field_changes",
    ):
        assert f'"{table_name}"' in migration


def test_expand_migration_makes_legacy_plaintext_credentials_nullable():
    migration = source("backend/alembic/versions/d88f6fdd4c31_stabilize_current_mvp_expand.py")
    assert 'op.alter_column("projects", "token", nullable=True)' in migration
    assert 'op.alter_column("projects", "creator_token", nullable=True)' in migration
    assert 'op.alter_column("votes", "session_id", nullable=True)' in migration
