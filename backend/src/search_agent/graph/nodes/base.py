from __future__ import annotations

from typing import Any

from langgraph.types import RunnableConfig


def configurable(config: RunnableConfig) -> dict[str, Any]:
    """Return merged `configurable` dict for node services (thread_id, llm, etc.)."""
    raw = config.get("configurable")
    return dict(raw) if isinstance(raw, dict) else {}
