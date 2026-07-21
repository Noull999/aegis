from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Action, Agent, AuditLog, AuditEventType
from app.schemas import ActionCreate


async def create_action(db: AsyncSession, data: ActionCreate) -> Action:
    """Register a new action request and emit an immutable audit event.

    In Phase 1 all actions are created with status ``pending`` and no policy
    decision is applied yet.
    """
    agent_result = await db.execute(select(Agent).where(Agent.id == data.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent is None:
        raise ValueError("Agent not found")
    if not agent.is_active:
        raise ValueError("Agent is inactive")

    action = Action(
        agent_id=data.agent_id,
        action_type=data.action_type,
        payload=dict(data.payload),
        context=dict(data.context),
        status="pending",
        decision=None,
        risk_score=None,
        resolution=None,
    )
    db.add(action)
    await db.flush()

    audit = AuditLog(
        action_id=action.id,
        event_type=AuditEventType.action_created.value,
        details={
            "agent_id": str(action.agent_id),
            "action_type": action.action_type,
            "payload": action.payload,
            "context": action.context,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)
    return action


async def get_action(db: AsyncSession, action_id: UUID) -> Optional[Action]:
    """Fetch an action by ID."""
    result = await db.execute(select(Action).where(Action.id == action_id))
    return result.scalar_one_or_none()
