from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db
from app.dependencies import get_db, get_redis
from app.routers import agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Aegis",
    description="Governance and permission layer for AI agents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agents.router)


@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Verify connectivity to the database and Redis."""
    db_ok = False
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False

    redis_ok = False
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "database": db_ok, "redis": redis_ok},
        )

    return {"status": "ok", "database": db_ok, "redis": redis_ok}
