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
    """Minimal in-memory Redis fake for health checks and Redis Streams."""

    def __init__(self):
        self._streams: dict = {}
        self._stream_seq = 0

    def _next_id(self) -> str:
        self._stream_seq += 1
        return f"{self._stream_seq}-0"

    async def ping(self):
        return True

    async def close(self):
        pass

    async def xadd(self, stream: str, fields: dict) -> str:
        if stream not in self._streams:
            self._streams[stream] = []
        msg_id = self._next_id()
        # Redis stores values as strings; mimic that loosely.
        self._streams[stream].append((msg_id, dict(fields)))
        return msg_id

    async def xread(self, streams: dict, count: int = 1, block: int = 0):
        # streams: {stream_key: last_id}
        # Return entries with IDs greater than last_id for each stream.
        result = []
        for stream_key, last_id in streams.items():
            entries = self._streams.get(stream_key, [])
            if last_id == "0":
                filtered = entries[-count:] if count else entries
            else:
                filtered = [e for e in entries if e[0] > last_id][-count:]
            if filtered:
                result.append([stream_key, filtered])
        return result

    async def xack(self, stream: str, group: str, *ids: str) -> int:
        return len(ids)


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
