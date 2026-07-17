from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Alembic and sync paths use the standard psycopg URL; async engine uses psycopg_async.
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgresql+psycopg://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg://", "postgresql+psycopg_async://", 1
    )
elif DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg_async://", 1)
else:
    ASYNC_DATABASE_URL = DATABASE_URL

engine = create_async_engine(ASYNC_DATABASE_URL, echo=settings.LOG_LEVEL == "DEBUG")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
