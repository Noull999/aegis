import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_action(client: AsyncClient):
    # Create an agent first
    r = await client.post("/agents", json={"name": "action-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    payload = {
        "agent_id": agent_id,
        "action_type": "send_email",
        "payload": {"to": "user@example.com", "subject": "Hello"},
        "context": {"source": "test"},
    }
    r = await client.post("/actions", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["agent_id"] == agent_id
    assert data["action_type"] == "send_email"
    assert data["payload"] == {"to": "user@example.com", "subject": "Hello"}
    assert data["status"] == "pending"
    assert data["decision"] == "review"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "get-action-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "read_file"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    r = await client.get(f"/actions/{action_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == action_id
    assert data["action_type"] == "read_file"


@pytest.mark.asyncio
async def test_create_action_invalid_agent(client: AsyncClient):
    payload = {
        "agent_id": "12345678-1234-1234-1234-123456789abc",
        "action_type": "send_email",
    }
    r = await client.post("/actions", json=payload)
    assert r.status_code == 400
    assert "Agent not found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_action_creates_audit_log(client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models import AuditLog

    r = await client.post("/agents", json={"name": "audit-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "list_files"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    from uuid import UUID
    result = await db_session.execute(select(AuditLog).where(AuditLog.action_id == UUID(action_id)))
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert any(log.event_type == "action_created" for log in logs)


@pytest.mark.asyncio
async def test_approve_pending_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "approve-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "send_email"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    action_id = data["id"]

    r = await client.post(f"/actions/{action_id}/approve", json={"reason": "Looks good"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "executed"
    assert data["resolution"]["decision"] == "approved"
    assert data["resolution"]["reason"] == "Looks good"


@pytest.mark.asyncio
async def test_reject_pending_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "reject-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "send_email"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    r = await client.post(f"/actions/{action_id}/reject", json={"reason": "Too risky"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert data["resolution"]["reason"] == "Too risky"


@pytest.mark.asyncio
async def test_cannot_approve_non_pending_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "nonpending-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "read_file"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    r = await client.post(f"/actions/{action_id}/approve", json={})
    assert r.status_code == 400
    assert "not pending" in r.json()["detail"]


@pytest.mark.asyncio
async def test_list_actions_filter_by_status(client: AsyncClient):
    r = await client.post("/agents", json={"name": "filter-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "send_email"})
    assert r.status_code == 201

    r = await client.get("/actions?status=pending")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(a["status"] == "pending" for a in data)
