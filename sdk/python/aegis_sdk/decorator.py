"""Aegis SDK decorator — wrap CrewAI tools with governance checks."""

import functools
import inspect
from typing import Any, Callable, Dict, Optional

from aegis_sdk.client import AegisClient


def aegis_guard(
    agent_id: str,
    action_type: Optional[str] = None,
    client: Optional[AegisClient] = None,
    auto_approve: bool = False,
    context: Optional[Dict[str, Any]] = None,
):
    """Decorator that gates a CrewAI tool through the Aegis governance layer.

    Before the wrapped function runs, Aegis receives an action request. Based on
    the policy decision:

    - ``approved``: the tool executes normally.
    - ``denied``: the tool is skipped and a denial message is returned.
    - ``pending``: the decorator polls/waits for human approval. If
      ``auto_approve`` is False and the timeout is reached, it returns a
      message indicating that the action is awaiting approval.

    Parameters
    ----------
    agent_id:
        UUID string of the agent registered in Aegis.
    action_type:
        Action type sent to Aegis. Defaults to the wrapped function name.
    client:
        ``AegisClient`` instance. If ``None``, a default client is created.
    auto_approve:
        If ``True``, automatically approve pending actions (useful for demos
        where the same script owns both the agent and the reviewer hat).
    context:
        Extra context attached to every action request.
    """

    def decorator(func: Callable) -> Callable:
        nonlocal action_type
        if action_type is None:
            action_type = func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal client
            sdk_client = client or AegisClient()
            payload = _build_payload(func, args, kwargs)
            action = sdk_client.submit_action(
                agent_id=agent_id,
                action_type=action_type,
                payload=payload,
                context=context or {},
            )

            status = action.get("status")
            action_id = action.get("id")

            if status == "approved":
                return func(*args, **kwargs)

            if status == "denied":
                return (
                    f"[Aegis DENIED] {action_type} was denied by policy "
                    f"(action_id={action_id})."
                )

            if status == "pending":
                if action_id is None:
                    return (
                        f"[Aegis PENDING] {action_type} was registered but no action_id was returned."
                    )
                if auto_approve:
                    sdk_client.approve(action_id, reason="auto-approved by SDK demo")
                    final = sdk_client.wait_for_decision(action_id)
                    if final.get("status") == "executed":
                        return func(*args, **kwargs)
                    return (
                        f"[Aegis PENDING] {action_type} was not executed "
                        f"(final status={final.get('status')})."
                    )

                final = sdk_client.wait_for_decision(action_id)
                if final.get("status") == "executed":
                    return func(*args, **kwargs)
                return (
                    f"[Aegis PENDING] {action_type} is awaiting human approval "
                    f"(action_id={action_id})."
                )

            # Fallback for any unexpected status.
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _build_payload(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Build a serializable payload from the function signature and call args."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        payload = dict(bound.arguments)
    except Exception:
        payload = {"args": args, "kwargs": kwargs}
    return _serialize(payload)


def _serialize(value: Any) -> Any:
    """Best-effort serialization to JSON-compatible primitives."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    return str(value)
