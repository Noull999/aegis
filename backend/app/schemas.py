from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent schemas
# ---------------------------------------------------------------------------
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    is_active: bool = True


class AgentRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    scopes: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AgentWithKeyRead(AgentRead):
    api_key: str


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------
class ActionCreate(BaseModel):
    agent_id: UUID
    action_type: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class ActionRead(BaseModel):
    id: UUID
    agent_id: UUID
    action_type: str
    payload: Dict[str, Any]
    context: Dict[str, Any]
    status: str
    decision: Optional[str]
    risk_score: Optional[float]
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ActionListParams(BaseModel):
    status: Optional[str] = None
    action_type: Optional[str] = None
    agent_id: Optional[UUID] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class ActionReviewRequest(BaseModel):
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audit log schemas
# ---------------------------------------------------------------------------
class AuditLogCreate(BaseModel):
    action_id: Optional[UUID] = None
    event_type: str = Field(..., min_length=1, max_length=50)
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(BaseModel):
    id: UUID
    action_id: Optional[UUID]
    event_type: str
    details: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Policy schemas
# ---------------------------------------------------------------------------
class PolicyCreate(BaseModel):
    action_type_pattern: str = Field(..., min_length=1, max_length=255)
    risk_level: str = Field(..., min_length=1, max_length=50)
    decision: str = Field(..., min_length=1, max_length=50)
    scopes_required: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    is_active: bool = True


class PolicyRead(BaseModel):
    id: UUID
    action_type_pattern: str
    risk_level: str
    decision: str
    scopes_required: List[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyUpdate(BaseModel):
    action_type_pattern: Optional[str] = Field(None, min_length=1, max_length=255)
    risk_level: Optional[str] = None
    decision: Optional[str] = None
    scopes_required: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
