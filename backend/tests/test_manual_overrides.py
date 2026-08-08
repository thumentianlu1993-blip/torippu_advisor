import pytest

from tests.contract_support import route_paths, table

pytestmark = pytest.mark.no_db


def test_all_editable_fields_have_versioned_override_and_change_models():
    overrides = table("candidate_field_overrides")
    changes = table("candidate_field_changes")
    assert overrides is not None and changes is not None
    assert {"candidate_id", "field_name", "value", "version"} <= set(overrides.columns.keys())
    assert {
        "candidate_id",
        "field_name",
        "old_value",
        "new_value",
        "restored_from_id",
        "actor_role",
        "version",
    } <= set(changes.columns.keys())


def test_manual_edit_history_restore_and_merge_review_are_token_scoped():
    paths = route_paths()
    expected = {
        "/api/projects/by-token/{share_token}/creator/candidates",
        "/api/projects/by-token/{share_token}/creator/candidates/{candidate_id}",
        "/api/projects/by-token/{share_token}/creator/candidates/{candidate_id}/history",
        "/api/projects/by-token/{share_token}/creator/candidates/{candidate_id}/restore",
        "/api/projects/by-token/{share_token}/creator/merge-proposals",
        "/api/projects/by-token/{share_token}/creator/merge-proposals/{proposal_id}/decision",
    }
    assert expected <= paths
