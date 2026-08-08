import pytest

from tests.contract_support import table

pytestmark = pytest.mark.no_db


def test_source_lifecycle_can_distinguish_qualifying_absence_runs():
    sources = table("candidate_sources")
    observations = table("source_observations")
    assert sources is not None and observations is not None
    assert {
        "consecutive_absences",
        "absence_window_started_at",
        "last_seen_at",
        "active",
    } <= set(sources.columns.keys())
    assert {"complete", "successful", "budget_truncated", "seen"} <= set(
        observations.columns.keys()
    )
