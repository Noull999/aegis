from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Policy
from app.schemas import PolicyCreate, PolicyUpdate


async def create_policy(db: AsyncSession, data: PolicyCreate) -> Policy:
    """Create a new policy rule."""
    policy = Policy(
        action_type_pattern=data.action_type_pattern,
        risk_level=data.risk_level,
        decision=data.decision,
        scopes_required=list(data.scopes_required),
        description=data.description,
        is_active=data.is_active,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def list_policies(db: AsyncSession, active_only: bool = True) -> List[Policy]:
    """Return all policies, optionally filtering active ones."""
    stmt = select(Policy)
    if active_only:
        stmt = stmt.where(Policy.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_policy(db: AsyncSession, policy_id: UUID) -> Optional[Policy]:
    """Fetch a policy by ID."""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    return result.scalar_one_or_none()


async def update_policy(db: AsyncSession, policy: Policy, data: PolicyUpdate) -> Policy:
    """Update policy fields."""
    if data.action_type_pattern is not None:
        policy.action_type_pattern = data.action_type_pattern
    if data.risk_level is not None:
        policy.risk_level = data.risk_level
    if data.decision is not None:
        policy.decision = data.decision
    if data.scopes_required is not None:
        policy.scopes_required = list(data.scopes_required)
    if data.description is not None:
        policy.description = data.description
    if data.is_active is not None:
        policy.is_active = data.is_active
    await db.commit()
    await db.refresh(policy)
    return policy


def _matches_pattern(action_type: str, pattern: str) -> bool:
    """Match an action type against a pattern.

    Supports exact match and wildcard ``*`` at the end. Keep it simple for MVP.
    """
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return action_type.startswith(pattern[:-1])
    return action_type == pattern


def _agent_has_scopes(agent: Agent, required: List[str]) -> bool:
    """Check whether the agent holds all required scopes."""
    if not required:
        return True
    agent_scopes = set(agent.scopes or [])
    return all(scope in agent_scopes for scope in required)


# Default risky action types that always require review if no policy says otherwise.
_DEFAULT_REVIEW_ACTIONS = {
    "send_email",
    "send_message",
    "delete",
    "remove",
    "pay",
    "purchase",
    "transfer",
    "execute",
    "deploy",
}


# OWASP-like risk scoring factors.
_RISK_LEVEL_SCORE = {
    "low": 10,
    "medium": 30,
    "high": 60,
    "critical": 90,
}


def _score_action(
    action_type: str,
    decision: str,
    matched_policy: Optional[Policy],
    agent_has_scopes: bool,
) -> float:
    """Compute a 0-100 risk score for an action.

    Higher score means higher risk. This is intentionally simple for the MVP.
    """
    score = 0.0

    if matched_policy is not None:
        score += _RISK_LEVEL_SCORE.get(matched_policy.risk_level, 30)
    else:
        # No explicit policy: higher base uncertainty.
        score += 25

    if action_type in _DEFAULT_REVIEW_ACTIONS:
        score += 15

    if not agent_has_scopes:
        score += 20

    if decision == "deny":
        score += 10

    return min(score, 100.0)


async def evaluate_action(
    db: AsyncSession,
    agent: Agent,
    action_type: str,
) -> Tuple[str, Optional[Policy], float]:
    """Evaluate an action against policies and return a decision + risk score.

    Returns a tuple of (decision, matched_policy, risk_score). Decision is one
    of: ``allow``, ``review``, ``deny``.
    """
    policies = await list_policies(db, active_only=True)

    # Find the first matching active policy.
    matched: Optional[Policy] = None
    for policy in policies:
        if _matches_pattern(action_type, policy.action_type_pattern):
            matched = policy
            break

    if matched is not None:
        has_scopes = _agent_has_scopes(agent, matched.scopes_required or [])
        if not has_scopes:
            return "deny", matched, _score_action(action_type, "deny", matched, False)
        return matched.decision, matched, _score_action(
            action_type, matched.decision, matched, True
        )

    # No explicit policy: default to review for risky actions, allow otherwise.
    if action_type in _DEFAULT_REVIEW_ACTIONS:
        return "review", None, _score_action(action_type, "review", None, True)

    return "allow", None, _score_action(action_type, "allow", None, True)
