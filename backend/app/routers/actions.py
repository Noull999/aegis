from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import ActionCreate, ActionRead
from app.services import action_service

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("", response_model=ActionRead, status_code=status.HTTP_201_CREATED)
async def create_action(data: ActionCreate, db: AsyncSession = Depends(get_db)):
    """Receive an action request from an agent.

    The action is stored with status ``pending`` and an immutable audit log
    entry is created. No policy decision is applied in Phase 1.
    """
    try:
        action = await action_service.create_action(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return action


@router.get("/{action_id}", response_model=ActionRead)
async def get_action(action_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve an action by ID."""
    action = await action_service.get_action(db, action_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return action
