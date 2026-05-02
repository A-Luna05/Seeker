"""Serialize LangGraph checkpoint values (e.g. LC messages) for JSON API responses."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


def _message_preview(m: BaseMessage) -> dict[str, Any]:
    if isinstance(m, HumanMessage):
        role = "human"
    elif isinstance(m, AIMessage):
        role = "ai"
    elif isinstance(m, SystemMessage):
        role = "system"
    elif isinstance(m, ToolMessage):
        role = "tool"
    else:
        role = m.__class__.__name__
    content = m.content
    if not isinstance(content, str):
        try:
            content = json.dumps(content, default=str)
        except (TypeError, ValueError):
            content = str(content)
    return {"role": role, "content": content}


def serialize_checkpoint_values(values: Any) -> Any:
    """Turn graph state into JSON-serializable structures."""
    if not isinstance(values, dict):
        try:
            return json.loads(json.dumps(values, default=str))
        except (TypeError, ValueError):
            return str(values)

    out: dict[str, Any] = {}
    for key, val in values.items():
        if key == "messages" and isinstance(val, (list, tuple)):
            out[key] = [
                _message_preview(item) if isinstance(item, BaseMessage) else json.loads(json.dumps(item, default=str))
                for item in val
            ]
            continue
        try:
            json.dumps(val, default=str)
            out[key] = val
        except (TypeError, ValueError):
            out[key] = json.loads(json.dumps(val, default=str))
    return out
