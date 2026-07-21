import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_risk_score_for_review_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "risk-review-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "send_email"})
    assert r.status_code == 201
    data = r.json()
    assert data["decision"] == "review"
    assert data["risk_score"] is not None
    assert data["risk_score"] > 0


@pytest.mark.asyncio
async def test_risk_score_for_allowed_action(client: AsyncClient):
    r = await client.post("/agents", json={"name": "risk-allow-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

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
    assert data["risk_score"] is not None
    assert data["risk_score"] < 50


@pytest.mark.asyncio
async def test_risk_score_for_denied_missing_scope(client: AsyncClient):
    r = await client.post("/agents", json={"name": "risk-deny-agent", "scopes": ["read"]})
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
    assert data["risk_score"] is not None
    assert data["risk_score"] >= 70
