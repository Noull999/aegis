import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient):
    r = await client.post("/agents", json={"name": "test-agent", "description": "Test agent", "scopes": ["read"]})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-agent"
    assert data["description"] == "Test agent"
    assert data["scopes"] == ["read"]
    assert data["is_active"] is True
    assert "api_key" in data
    assert data["api_key"].startswith("aegis_")


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient):
    r = await client.post("/agents", json={"name": "get-agent", "scopes": ["write"]})
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r = await client.get(f"/agents/{agent_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == agent_id
    assert data["name"] == "get-agent"
    assert "api_key" not in data


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    r = await client.get("/agents/12345678-1234-1234-1234-123456789abc")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client: AsyncClient):
    payload = {"name": "duplicate-agent"}
    r = await client.post("/agents", json=payload)
    assert r.status_code == 201

    r = await client.post("/agents", json=payload)
    assert r.status_code == 400
