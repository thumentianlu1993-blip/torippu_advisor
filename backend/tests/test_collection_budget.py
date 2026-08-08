import pytest

from tests.contract_support import source, table

pytestmark = pytest.mark.no_db


def test_external_call_reservations_are_persisted_with_stable_idempotency_key():
    reservations = table("external_call_reservations")
    assert reservations is not None
    assert {
        "project_id",
        "run_id",
        "provider",
        "idempotency_key",
        "request_units",
        "estimated_cost_usd",
        "status",
        "operation_owner",
        "operation_started_at",
        "response_payload",
    } <= set(reservations.columns.keys())
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in reservations.constraints
        if hasattr(constraint, "columns")
    }
    assert ("idempotency_key",) in unique_columns


def test_provider_transport_declares_all_frozen_limits_and_reserves_before_send():
    transport = source("backend/app/services/provider_transport.py")
    for expected in ("150", "500", "2", "40", "0.40", "0.50"):
        assert expected in transport
    assert transport.index("reserve") < transport.index("send")
    assert "DENY_EXTERNAL_NETWORK" in transport
