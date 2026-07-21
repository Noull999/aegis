import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActionStatus(str, PyEnum):
    pending = "pending"
    approved = "approved"
    denied = "denied"
    reviewed = "reviewed"


class ActionDecision(str, PyEnum):
    allow = "allow"
    review = "review"
    deny = "deny"


class AuditEventType(str, PyEnum):
    action_created = "action_created"
    action_decided = "action_decided"
    action_executed = "action_executed"
    policy_matched = "policy_matched"
    agent_registered = "agent_registered"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    api_key_hash = Column(String(128), nullable=False, index=True)
    scopes = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    actions = relationship("Action", back_populates="agent", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(255), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    context = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default=ActionStatus.pending.value)
    decision = Column(String(50), nullable=True)
    risk_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(JSON, nullable=True)

    agent = relationship("Agent", back_populates="actions")
    audit_logs = relationship("AuditLog", back_populates="action", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(UUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    details = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    action = relationship("Action", back_populates="audit_logs")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type_pattern = Column(String(255), nullable=False, index=True)
    risk_level = Column(String(50), nullable=False)
    decision = Column(String(50), nullable=False)
    scopes_required = Column(JSON, nullable=False, default=list)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
