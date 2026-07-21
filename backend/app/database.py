from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings


def _create_engine(database_url: str):
    """Create an async engine with sensible defaults for SQLite and PostgreSQL."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(
        database_url,
        echo=False,
        future=True,
        poolclass=NullPool if database_url.startswith("sqlite") else None,
        connect_args=connect_args,
    )


engine = _create_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables. Useful for development; production should use Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
