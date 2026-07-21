from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import PolicyCreate, PolicyRead, PolicyUpdate
from app.services import policy_service

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy(data: PolicyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new policy rule."""
    return await policy_service.create_policy(db, data)


@router.get("", response_model=list[PolicyRead])
async def list_policies(db: AsyncSession = Depends(get_db)):
    """List all active policies."""
    return await policy_service.list_policies(db, active_only=True)


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a policy by ID."""
    policy = await policy_service.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy


@router.patch("/{policy_id}", response_model=PolicyRead)
async def update_policy(policy_id: UUID, data: PolicyUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing policy."""
    policy = await policy_service.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return await policy_service.update_policy(db, policy, data)
