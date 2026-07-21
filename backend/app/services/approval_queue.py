import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis

STREAM_KEY = "aegis:pending_actions"
CONSUMER_GROUP = "aegis-approvers"


def _flatten_fields(fields: Dict[str, Any]) -> Dict[str, str]:
    """Serialize stream fields to strings because Redis Streams only accept
    bytes, strings, ints or floats as field values.
    """
    result: Dict[str, str] = {}
    for key, value in fields.items():
        if isinstance(value, (dict, list)):
            result[key] = json.dumps(value)
        else:
            result[key] = str(value)
    return result


async def push_pending_action(
    redis_client: redis.Redis, action_id: UUID, action_data: Dict[str, Any]
) -> str:
    """Push an action that needs human approval onto a Redis Stream.

    Returns the message ID assigned by Redis.
    """
    payload = {
        "action_id": str(action_id),
        "action_type": action_data.get("action_type", ""),
        "agent_id": str(action_data.get("agent_id", "")),
        "payload": action_data.get("payload", {}),
        "context": action_data.get("context", {}),
        "decision": action_data.get("decision", "review"),
    }
    msg_id = await redis_client.xadd(STREAM_KEY, _flatten_fields(payload))
    return msg_id


async def read_pending_actions(
    redis_client: redis.Redis, count: int = 50, block_ms: int = 1000
) -> List[Dict[str, Any]]:
    """Read new pending actions from the stream without consuming them.

    This is used by the dashboard to discover actions that need review.
    """
    try:
        entries = await redis_client.xread({STREAM_KEY: "0"}, count=count, block=block_ms)
    except Exception:
        return []

    results: List[Dict[str, Any]] = []
    for _stream_key, messages in entries:
        for msg_id, fields in messages:
            row: Dict[str, Any] = {"stream_id": msg_id}
            for key, value in fields.items():
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                row[key] = value
            results.append(row)
    return results


async def acknowledge_action(redis_client: redis.Redis, stream_id: str) -> bool:
    """Acknowledge (remove from pending consumers) a stream entry.

    Returns True if the entry was acknowledged, False otherwise.
    """
    acked = await redis_client.xack(STREAM_KEY, CONSUMER_GROUP, stream_id)
    return bool(acked)
