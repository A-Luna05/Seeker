from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    """One step in the agent run, for PDF and API."""

    node: str
    title: str
    detail: str = ""
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "title": self.title,
            "detail": self.detail,
            "ts": self.ts.isoformat(),
        }

    @classmethod
    def from_state_dict(cls, d: dict[str, Any]) -> TraceStep:
        ts = d.get("ts")
        if isinstance(ts, str):
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            parsed = datetime.now(UTC)
        return cls(
            node=str(d.get("node", "")),
            title=str(d.get("title", "")),
            detail=str(d.get("detail", "")),
            ts=parsed,
        )


def trace_steps_from_state(raw: list[dict[str, Any]] | None) -> list[TraceStep]:
    if not raw:
        return []
    return [TraceStep.from_state_dict(x) for x in raw]
