"""Audit log service with filtering capabilities."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def list_audit_logs(
    db: AsyncSession,
    action_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[AuditLog]:
    """Return audit logs with optional filters."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action_id is not None:
        stmt = stmt.where(AuditLog.action_id == action_id)
    if event_type is not None:
        stmt = stmt.where(AuditLog.event_type == event_type)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())
