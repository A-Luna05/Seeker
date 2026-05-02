from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    mime_type: str
    label: str
    data_base64: str


class RunAgentRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    thread_id: str | None = Field(None, max_length=128)
    model: str | None = Field(None, max_length=256)
    include_pdf: bool = False


class RunAgentResponse(BaseModel):
    thread_id: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    run_trace: list[dict[str, Any]] = Field(default_factory=list)
    pdf_base64: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)


class CheckpointSummary(BaseModel):
    checkpoint_id: str | None = None
    thread_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckpointListResponse(BaseModel):
    thread_id: str
    checkpoints: list[CheckpointSummary]


class CheckpointStateResponse(BaseModel):
    """Full graph channel values at a checkpoint (not just checkpoint metadata)."""

    thread_id: str
    checkpoint_id: str | None = None
    created_at: str | None = None
    parent_checkpoint_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    next: list[str] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)
