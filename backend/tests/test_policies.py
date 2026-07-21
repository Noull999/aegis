import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_policy(client: AsyncClient):
    payload = {
        "action_type_pattern": "read_*",
        "risk_level": "low",
        "decision": "allow",
        "scopes_required": ["read"],
        "description": "Allow read operations",
    }
    r = await client.post("/policies", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["action_type_pattern"] == "read_*"
    assert data["decision"] == "allow"
    assert data["risk_level"] == "low"
    assert data["scopes_required"] == ["read"]


@pytest.mark.asyncio
async def test_list_policies(client: AsyncClient):
    r = await client.post(
        "/policies",
        json={
            "action_type_pattern": "delete_*",
            "risk_level": "high",
            "decision": "deny",
            "scopes_required": [],
        },
    )
    assert r.status_code == 201

    r = await client.get("/policies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_policy_allow_action(client: AsyncClient):
    # Create agent with read scope
    r = await client.post("/agents", json={"name": "reader-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    # Policy allows read_file
    r = await client.post(
        "/policies",
        json={
            "action_type_pattern": "read_file",
            "risk_level": "low",
            "decision": "allow",
            "scopes_required": ["read"],
        },
    )
    assert r.status_code == 201

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "read_file"})
    assert r.status_code == 201
    data = r.json()
    assert data["decision"] == "allow"
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_policy_deny_missing_scope(client: AsyncClient):
    # Agent without required scope
    r = await client.post("/agents", json={"name": "limited-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post(
        "/policies",
        json={
            "action_type_pattern": "delete_file",
            "risk_level": "high",
            "decision": "allow",
            "scopes_required": ["admin"],
        },
    )
    assert r.status_code == 201

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "delete_file"})
    assert r.status_code == 201
    data = r.json()
    assert data["decision"] == "deny"
    assert data["status"] == "denied"


@pytest.mark.asyncio
async def test_default_review_for_risky_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "email-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    # No policy for send_email; default behavior should be review
    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "send_email"})
    assert r.status_code == 201
    data = r.json()
    assert data["decision"] == "review"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_wildcard_policy_pattern(client: AsyncClient):
    r = await client.post("/agents", json={"name": "wildcard-agent", "scopes": ["admin"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post(
        "/policies",
        json={
            "action_type_pattern": "admin_*",
            "risk_level": "medium",
            "decision": "allow",
            "scopes_required": ["admin"],
        },
    )
    assert r.status_code == 201

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "admin_purge"})
    assert r.status_code == 201
    data = r.json()
    assert data["decision"] == "allow"
