import pytest

from tests.contract_support import table

pytestmark = pytest.mark.no_db


def test_candidate_source_identity_and_provisional_state_are_first_class():
    sources = table("candidate_sources")
    assert sources is not None
    required = {
        "candidate_id",
        "identity_provider",
        "entity_type",
        "external_id",
        "canonical_url",
        "fallback_fingerprint",
        "identity_state",
        "collector_vendor",
        "collector_version",
    }
    assert required <= set(sources.columns.keys())


def test_manual_candidates_have_internal_uuid_and_origin_marker():
    candidates = table("candidates")
    assert candidates is not None
    assert {"public_id", "origin", "active", "version"} <= set(candidates.columns.keys())
