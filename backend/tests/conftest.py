import os
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TRAVEL_TEST_DATABASE_URL", "")
DISPOSABLE_DB_ENABLED = os.getenv("TRAVEL_DISPOSABLE_DB") == "1"


def _validated_test_urls() -> tuple[str, str, str]:
    """Return async target/admin URLs only for an explicit disposable test DB."""
    if not TEST_DATABASE_URL:
        raise pytest.UsageError(
            "database tests require an explicit TRAVEL_TEST_DATABASE_URL; "
            "the inherited DATABASE_URL is intentionally ignored"
        )
    if not DISPOSABLE_DB_ENABLED:
        raise pytest.UsageError("set TRAVEL_DISPOSABLE_DB=1 for database tests")

    parsed = urlsplit(TEST_DATABASE_URL)
    database_name = parsed.path.removeprefix("/")
    if parsed.scheme not in {"postgresql+psycopg", "postgresql+psycopg_async"}:
        raise pytest.UsageError("TRAVEL_TEST_DATABASE_URL must use PostgreSQL psycopg")
    if not database_name.startswith("travel_test_"):
        raise pytest.UsageError("disposable database name must start with travel_test_")

    async_scheme = "postgresql+psycopg_async"
    target_url = urlunsplit(parsed._replace(scheme=async_scheme))
    admin_url = urlunsplit(parsed._replace(scheme=async_scheme, path="/postgres"))
    return target_url, admin_url, database_name


def _test_engine():
    target_url, _, _ = _validated_test_urls()
    return create_async_engine(target_url, echo=False)


async def create_test_database():
    """Create only the explicitly named disposable test database."""
    _, admin_url, database_name = _validated_test_urls()
    admin_engine = create_async_engine(admin_url, echo=False, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:database_name"),
            {"database_name": database_name},
        )
        if not result.scalar_one_or_none():
            # The prefix check above makes the identifier bounded; quote it defensively.
            quoted_name = database_name.replace('"', '""')
            await conn.execute(text(f'CREATE DATABASE "{quoted_name}"'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    await create_test_database()
    engine = _test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    engine = _test_engine()
    test_session_local = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with test_session_local() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://test",
        headers={"Origin": "http://localhost:3000"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
