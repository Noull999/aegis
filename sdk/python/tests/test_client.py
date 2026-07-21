"""Unit tests for the Aegis SDK client."""

import pytest
import responses

from aegis_sdk import AegisClient


@responses.activate
def test_submit_action_approved():
    responses.post(
        "http://localhost:8000/actions",
        json={
            "id": "11111111-1111-1111-1111-111111111111",
            "status": "approved",
            "decision": "allow",
        },
        status=201,
    )

    client = AegisClient()
    result = client.submit_action(
        agent_id="22222222-2222-2222-2222-222222222222",
        action_type="read_file",
        payload={"path": "/tmp/foo"},
    )
    assert result["status"] == "approved"


@responses.activate
def test_wait_for_decision():
    action_id = "11111111-1111-1111-1111-111111111111"
    responses.get(
        f"http://localhost:8000/actions/{action_id}",
        json={"id": action_id, "status": "executed"},
        status=200,
    )

    client = AegisClient(poll_interval=0.01, max_poll_time=0.1)
    result = client.wait_for_decision(action_id)
    assert result["status"] == "executed"


@responses.activate
def test_approve():
    action_id = "11111111-1111-1111-1111-111111111111"
    responses.post(
        f"http://localhost:8000/actions/{action_id}/approve",
        json={"id": action_id, "status": "executed"},
        status=200,
    )

    client = AegisClient()
    result = client.approve(action_id, reason="test")
    assert result["status"] == "executed"
