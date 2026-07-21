"""Demo: wrap a CrewAI-style tool with the Aegis governance SDK.

This script:
1. Registers a dummy agent in Aegis (or reuses one passed via env).
2. Defines a tool that writes a file.
3. Wraps it with ``@aegis_guard``.
4. Calls the tool with ``auto_approve=True`` so the demo can run end-to-end.

Run Aegis backend first:
    cd /root/aegis/backend && source .venv/bin/activate && uvicorn app.main:app

Then run this demo:
    cd /root/aegis/sdk/examples && python crewai_guard_demo.py
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

import requests

from aegis_sdk import AegisClient, aegis_guard

AEGIS_URL = os.getenv("AEGIS_URL", "http://localhost:8000")


def ensure_agent() -> str:
    """Create a dummy agent in Aegis for this demo."""
    name = f"sdk-demo-agent-{uuid.uuid4().hex[:8]}"
    r = requests.post(
        f"{AEGIS_URL}/agents",
        json={"name": name, "scopes": ["write"]},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["id"]


@aegis_guard(
    agent_id=os.getenv("AEGIS_AGENT_ID") or ensure_agent(),
    action_type="write_file",
    auto_approve=True,
)
def write_file_tool(path: str, content: str) -> str:
    """CrewAI-style tool that writes a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} chars to {path}"


if __name__ == "__main__":
    print(f"Aegis URL: {AEGIS_URL}")
    result = write_file_tool("/tmp/aegis_demo_file.txt", "hello from crewai guard")
    print(result)
