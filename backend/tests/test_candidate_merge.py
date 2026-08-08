import pytest

from tests.contract_support import table

pytestmark = pytest.mark.no_db


def test_merge_review_and_vote_conflict_audit_models_exist():
    proposals = table("merge_proposals")
    merge_audit = table("candidate_merge_audits")
    vote_audit = table("vote_merge_conflict_audits")
    assert proposals is not None and merge_audit is not None and vote_audit is not None
    assert {"score", "reasons", "status", "supersession_key"} <= set(proposals.columns.keys())
    assert {"survivor_candidate_id", "loser_candidate_id"} <= set(merge_audit.columns.keys())
    assert {"kept_vote_id", "discarded_vote_id"} <= set(vote_audit.columns.keys())
