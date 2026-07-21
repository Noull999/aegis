import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_audit_logs(client: AsyncClient):
    r = await client.post("/agents", json={"name": "audit-list-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "read_file"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    r = await client.get("/audit")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(log["event_type"] == "action_created" for log in data)


@pytest.mark.asyncio
async def test_filter_audit_logs_by_action_id(client: AsyncClient):
    r = await client.post("/agents", json={"name": "audit-filter-agent", "scopes": ["read"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.post("/actions", json={"agent_id": agent_id, "action_type": "read_file"})
    assert r.status_code == 201
    action_id = r.json()["id"]

    r = await client.get(f"/audit?action_id={action_id}")
    assert r.status_code == 200
    data = r.json()
    assert all(log["action_id"] == action_id for log in data)
    assert any(log["event_type"] == "action_created" for log in data)


@pytest.mark.asyncio
async def test_filter_audit_logs_by_event_type(client: AsyncClient):
    r = await client.get("/audit?event_type=action_created&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert all(log["event_type"] == "action_created" for log in data)
