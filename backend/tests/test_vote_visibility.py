import pytest

from app.schemas import CandidateRead, VoteRead
from tests.contract_support import route_paths

pytestmark = pytest.mark.no_db


def test_vote_route_is_nested_under_share_token_and_vote_identity_is_private():
    assert "/api/projects/by-token/{share_token}/candidates/{candidate_id}/votes" in route_paths()
    assert "session_id" not in VoteRead.model_fields
    assert "voter_hash" not in VoteRead.model_fields


def test_public_candidate_contract_can_omit_hidden_aggregates_but_return_own_vote():
    fields = CandidateRead.model_fields
    assert "user_vote" in fields
    for count in ("like_count", "dislike_count", "neutral_count"):
        assert fields[count].default is None


def test_creator_visibility_toggle_and_private_export_routes_exist():
    paths = route_paths()
    assert "/api/projects/by-token/{share_token}/creator/votes-visibility" in paths
    assert "/api/projects/by-token/{share_token}/creator/export/google-maps" in paths
