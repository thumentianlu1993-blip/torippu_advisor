import pytest

from tests.contract_support import source

pytestmark = pytest.mark.no_db


def test_trusted_client_ip_and_ipv6_64_normalization_contract_exists():
    config = source("backend/app/config.py")
    assert "TRUSTED_PROXY_CIDRS" in config
    limiter = source("backend/app/services/rate_limits.py")
    assert "IPv6Network" in limiter or "/64" in limiter
    assert "X-Forwarded-For" in limiter


def test_creation_recollection_and_vote_limits_are_declared():
    limiter = source("backend/app/services/rate_limits.py")
    for expected in (
        "CREATE_HOURLY_LIMIT = 3",
        "CREATE_DAILY_LIMIT = 10",
        "RECOLLECT_HOURLY_LIMIT = 1",
        "RECOLLECT_DAILY_LIMIT = 6",
        "VOTE_TEN_MINUTE_LIMIT = 60",
        "VOTE_DAILY_LIMIT = 300",
        "VOTE_CHANGE_DAILY_LIMIT = 10",
    ):
        assert expected in limiter


def test_rate_limited_create_is_checked_before_project_write():
    projects = source("backend/app/routers/projects.py")
    assert "enforce_project_create_limit" in projects
    assert projects.index("enforce_project_create_limit") < projects.index("create_project(")
