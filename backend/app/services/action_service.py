from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Action, Agent, AuditLog, AuditEventType
from app.schemas import ActionCreate
from app.services import policy_service


async def create_action(db: AsyncSession, data: ActionCreate) -> Action:
    """Register a new action request, evaluate policies, and audit the event.

    The action is persisted with the decision returned by the policy engine.
    Status mapping:
      - ``allow``  -> ``approved``
      - ``review`` -> ``pending``
      - ``deny``   -> ``denied``
    """
    agent_result = await db.execute(select(Agent).where(Agent.id == data.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent is None:
        raise ValueError("Agent not found")
    if not agent.is_active:
        raise ValueError("Agent is inactive")

    decision, matched_policy = await policy_service.evaluate_action(
        db, agent, data.action_type
    )

    status_map = {"allow": "approved", "review": "pending", "deny": "denied"}
    action_status = status_map.get(decision, "pending")

    action = Action(
        agent_id=data.agent_id,
        action_type=data.action_type,
        payload=dict(data.payload),
        context=dict(data.context),
        status=action_status,
        decision=decision,
        risk_score=None,
        resolution=None,
    )
    db.add(action)
    await db.flush()

    audit_details = {
        "agent_id": str(action.agent_id),
        "action_type": action.action_type,
        "payload": action.payload,
        "context": action.context,
        "decision": decision,
        "policy_id": str(matched_policy.id) if matched_policy else None,
    }
    audit = AuditLog(
        action_id=action.id,
        event_type=AuditEventType.action_created.value,
        details=audit_details,
    )
    db.add(audit)

    # Also log the policy decision as a separate immutable audit event.
    if decision in ("allow", "deny"):
        decision_audit = AuditLog(
            action_id=action.id,
            event_type=AuditEventType.action_decided.value,
            details={
                "decision": decision,
                "policy_id": str(matched_policy.id) if matched_policy else None,
                "reason": "policy_matched" if matched_policy else "default",
            },
        )
        db.add(decision_audit)

    await db.commit()
    await db.refresh(action)
    return action


async def get_action(db: AsyncSession, action_id: UUID) -> Optional[Action]:
    """Fetch an action by ID."""
    result = await db.execute(select(Action).where(Action.id == action_id))
    return result.scalar_one_or_none()
