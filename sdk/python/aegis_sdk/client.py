"""Aegis SDK client — submit actions and wait for policy decisions."""

import os
import time
from typing import Any, Dict, Optional
from uuid import UUID

import requests


class AegisClient:
    """HTTP client for the Aegis governance API.

    The client registers action requests and polls for a final decision when
    Aegis returns a ``pending`` status.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        poll_interval: float = 1.0,
        max_poll_time: float = 60.0,
    ):
        self.base_url = (base_url or os.getenv("AEGIS_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.getenv("AEGIS_API_KEY", "")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def submit_action(
        self,
        agent_id: str,
        action_type: str,
        payload: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit an action request to Aegis and return the action record."""
        url = f"{self.base_url}/actions"
        body = {
            "agent_id": agent_id,
            "action_type": action_type,
            "payload": payload or {},
            "context": context or {},
        }
        response = requests.post(
            url, json=body, headers=self._headers(), timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_action(self, action_id: str) -> Dict[str, Any]:
        """Fetch a single action by ID."""
        url = f"{self.base_url}/actions/{action_id}"
        response = requests.get(url, headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def wait_for_decision(self, action_id: str) -> Dict[str, Any]:
        """Poll an action until it leaves ``pending`` status.

        Returns the final action record. If the timeout is reached while still
        pending, returns the action as-is so the caller can decide what to do.
        """
        deadline = time.monotonic() + self.max_poll_time
        while time.monotonic() < deadline:
            action = self.get_action(action_id)
            if action.get("status") != "pending":
                return action
            time.sleep(self.poll_interval)
        return self.get_action(action_id)

    def approve(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """Approve a pending action via the Aegis API."""
        url = f"{self.base_url}/actions/{action_id}/approve"
        response = requests.post(
            url, json={"reason": reason}, headers=self._headers(), timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def reject(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending action via the Aegis API."""
        url = f"{self.base_url}/actions/{action_id}/reject"
        response = requests.post(
            url, json={"reason": reason}, headers=self._headers(), timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
