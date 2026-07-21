from typing import AsyncGenerator

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db as _get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency wrapper that exposes the async database session."""
    async for session in _get_db():
        yield session


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Dependency wrapper that exposes a Redis async connection."""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()
