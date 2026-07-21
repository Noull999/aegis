from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Action, ActionStatus, Agent, AuditLog, AuditEventType
from app.schemas import ActionCreate, ActionReviewRequest
from app.services import approval_queue, policy_service


async def create_action(
    db: AsyncSession, redis_client: redis.Redis, data: ActionCreate
) -> Action:
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

    decision, matched_policy, risk_score = await policy_service.evaluate_action(
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
        risk_score=risk_score,
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

    # Push to the approval queue if the action needs human review.
    if decision == "review":
        await approval_queue.push_pending_action(
            redis_client,
            action.id,
            {
                "agent_id": str(action.agent_id),
                "action_type": action.action_type,
                "payload": action.payload,
                "context": action.context,
                "decision": decision,
            },
        )

    return action


async def list_actions(
    db: AsyncSession,
    status: Optional[str] = None,
    action_type: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Action]:
    """List actions with optional filters."""
    stmt = select(Action).order_by(Action.created_at.desc())
    if status is not None:
        stmt = stmt.where(Action.status == status)
    if action_type is not None:
        stmt = stmt.where(Action.action_type == action_type)
    if agent_id is not None:
        stmt = stmt.where(Action.agent_id == agent_id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _resolve_action(
    db: AsyncSession,
    action_id: UUID,
    new_status: str,
    review_data: ActionReviewRequest,
) -> Action:
    """Shared helper to approve or reject an action and audit the event."""
    action = await get_action(db, action_id)
    if action is None:
        raise ValueError("Action not found")
    if action.status != ActionStatus.pending.value:
        raise ValueError(f"Action is not pending (current status: {action.status})")

    action.status = new_status
    action.resolved_at = datetime.now(timezone.utc)
    action.resolution = {
        "decision": new_status,
        "reason": review_data.reason,
        "metadata": review_data.metadata,
    }

    audit = AuditLog(
        action_id=action.id,
        event_type=AuditEventType.action_decided.value,
        details={
            "decision": new_status,
            "reason": review_data.reason,
            "metadata": review_data.metadata,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)
    return action


async def approve_action(
    db: AsyncSession,
    redis_client: redis.Redis,
    action_id: UUID,
    review_data: ActionReviewRequest,
) -> Action:
    """Approve a pending action and attempt a best-effort execution step.

    For this MVP, execution is simulated: the action is marked as ``executed``
    immediately after approval. In a production system, this would hand off to
    an executor worker.
    """
    action = await _resolve_action(db, action_id, ActionStatus.approved.value, review_data)

    # Simulate execution.
    action.status = ActionStatus.executed.value
    action.resolution["executed_at"] = datetime.now(timezone.utc).isoformat()
    db.add(action)

    execution_audit = AuditLog(
        action_id=action.id,
        event_type=AuditEventType.action_executed.value,
        details={
            "status": "executed",
            "resolution": action.resolution,
        },
    )
    db.add(execution_audit)
    await db.commit()
    await db.refresh(action)

    # Best-effort cleanup from the approval queue.
    try:
        pending = await approval_queue.read_pending_actions(redis_client, count=200, block_ms=10)
        for entry in pending:
            if entry.get("action_id") == str(action_id):
                await approval_queue.acknowledge_action(redis_client, entry["stream_id"])
                break
    except Exception:
        pass

    return action


async def reject_action(
    db: AsyncSession,
    redis_client: redis.Redis,
    action_id: UUID,
    review_data: ActionReviewRequest,
) -> Action:
    """Reject a pending action."""
    action = await _resolve_action(db, action_id, ActionStatus.rejected.value, review_data)

    # Best-effort cleanup from the approval queue.
    try:
        pending = await approval_queue.read_pending_actions(redis_client, count=200, block_ms=10)
        for entry in pending:
            if entry.get("action_id") == str(action_id):
                await approval_queue.acknowledge_action(redis_client, entry["stream_id"])
                break
    except Exception:
        pass

    return action


async def get_action(db: AsyncSession, action_id: UUID) -> Optional[Action]:
    """Fetch an action by ID."""
    result = await db.execute(select(Action).where(Action.id == action_id))
    return result.scalar_one_or_none()
