"""Audit log router."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import AuditLogRead
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    action_id: Optional[UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with optional filters by action_id and event_type."""
    return await audit_service.list_audit_logs(
        db, action_id=action_id, event_type=event_type, limit=limit, offset=offset
    )
