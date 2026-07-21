import hashlib
import secrets
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent
from app.schemas import AgentCreate, AgentUpdate


def _hash_api_key(key: str) -> str:
    """Hash a raw API key using SHA-256."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _generate_api_key() -> str:
    """Generate a new raw API key."""
    return f"aegis_{secrets.token_urlsafe(32)}"


async def create_agent(db: AsyncSession, data: AgentCreate) -> Tuple[Agent, str]:
    """Create a new agent and return it with its raw API key."""
    raw_key = _generate_api_key()
    agent = Agent(
        name=data.name,
        description=data.description,
        api_key_hash=_hash_api_key(raw_key),
        scopes=list(data.scopes),
        is_active=data.is_active,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent, raw_key


async def get_agent(db: AsyncSession, agent_id: UUID) -> Optional[Agent]:
    """Fetch an agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def update_agent(db: AsyncSession, agent: Agent, data: AgentUpdate) -> Agent:
    """Update agent fields and persist changes."""
    if data.name is not None:
        agent.name = data.name
    if data.description is not None:
        agent.description = data.description
    if data.scopes is not None:
        agent.scopes = list(data.scopes)
    if data.is_active is not None:
        agent.is_active = data.is_active
    await db.commit()
    await db.refresh(agent)
    return agent
