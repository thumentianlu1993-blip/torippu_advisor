from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

ASYNC_DATABASE_URL = (settings.DATABASE_URL.rsplit("/", 1)[0] + "/travel_test").replace(
    "postgresql+psycopg://", "postgresql+psycopg_async://"
)

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_test_database():
    """Create the test database if it doesn't exist."""
    # Connect to the main travel database with the travel user to create travel_test.
    admin_url = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg_async://")
    admin_engine = create_async_engine(admin_url, echo=False, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='travel_test'")
        )
        if not result.scalar_one_or_none():
            await conn.execute(text("CREATE DATABASE travel_test"))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    await create_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
