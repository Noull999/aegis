import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point the application at the test database before importing app/config.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test_aegis.db"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import Base, engine, get_db  # noqa: E402
from app.dependencies import get_redis  # noqa: E402
from app.main import app  # noqa: E402


TestSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class FakeRedis:
    """Minimal in-memory Redis fake for health checks."""

    async def ping(self):
        return True

    async def close(self):
        pass


async def override_get_redis() -> AsyncGenerator[FakeRedis, None]:
    yield FakeRedis()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_redis] = override_get_redis


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_test_database():
    """Ensure the test database schema exists before running tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
