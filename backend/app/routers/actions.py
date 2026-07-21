from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis
from app.schemas import ActionCreate, ActionListParams, ActionRead, ActionReviewRequest
from app.services import action_service

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("", response_model=ActionRead, status_code=status.HTTP_201_CREATED)
async def create_action(
    data: ActionCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Receive an action request from an agent.

    The action is evaluated against policies. If it needs review, it is pushed
    onto a Redis Stream for human approval.
    """
    try:
        action = await action_service.create_action(db, redis_client, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return action


@router.get("", response_model=list[ActionRead])
async def list_actions(
    status: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    agent_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List actions with optional filters."""
    params = ActionListParams(
        status=status, action_type=action_type, agent_id=agent_id, limit=limit, offset=offset
    )
    return await action_service.list_actions(
        db,
        status=params.status,
        action_type=params.action_type,
        agent_id=params.agent_id,
        limit=params.limit,
        offset=params.offset,
    )


@router.get("/{action_id}", response_model=ActionRead)
async def get_action(action_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve an action by ID."""
    action = await action_service.get_action(db, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return action


@router.post("/{action_id}/approve", response_model=ActionRead)
async def approve_action(
    action_id: UUID,
    data: ActionReviewRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Approve a pending action and simulate execution."""
    try:
        action = await action_service.approve_action(db, redis_client, action_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return action


@router.post("/{action_id}/reject", response_model=ActionRead)
async def reject_action(
    action_id: UUID,
    data: ActionReviewRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Reject a pending action."""
    try:
        action = await action_service.reject_action(db, redis_client, action_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return action
