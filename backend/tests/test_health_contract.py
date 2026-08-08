import pytest

from tests.contract_support import source

pytestmark = pytest.mark.no_db


def test_health_response_never_serializes_exception_text():
    main = source("backend/app/main.py")
    assert '"database": str(exc)' not in main
    assert '"status": "degraded"' in main
